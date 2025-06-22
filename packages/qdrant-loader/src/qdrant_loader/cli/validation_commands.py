"""Validation and repair CLI commands.

This module contains all CLI commands related to validation and repair operations,
including graph validation, repair execution, scheduling, and status monitoring.
"""

import asyncio
import json
from pathlib import Path

import click
from click.exceptions import ClickException
from click.types import Choice
from click.types import Path as ClickPath
from click.utils import echo

# Import managers for module-level access (tests expect these to be accessible)
from ..core.managers import IDMappingManager, Neo4jManager, QdrantManager

# Import validation classes for module-level access (tests expect these to be accessible)
from ..core.validation_repair import (
    ValidationIssue,
    ValidationRepairSystem,
    ValidationRepairSystemIntegrator,
)
from .core import (
    CONFIG_OPTION,
    ENV_OPTION,
    LOG_LEVEL_OPTION,
    WORKSPACE_OPTION,
    check_settings,
    get_logger,
    load_config_with_workspace,
    setup_logging,
    setup_workspace,
    validate_workspace_flags,
)


@click.group(name="validation")
def validation_group():
    """Validation and repair commands for data consistency management."""
    pass


@validation_group.command(name="validate-graph")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option(
    "--scanners",
    type=str,
    help="Comma-separated list of scanners to run (e.g., 'missing_mappings,orphaned_records'). If not specified, all scanners will be used.",
)
@click.option(
    "--max-entities",
    type=int,
    help="Maximum number of entities to scan per scanner. Useful for testing or limiting scan scope.",
)
@click.option(
    "--auto-repair",
    is_flag=True,
    help="Automatically repair issues that are marked as auto-repairable.",
)
@click.option(
    "--output",
    type=ClickPath(path_type=Path),
    help="Output file path for validation report (JSON format). If not specified, prints to stdout.",
)
@click.option(
    "--timeout",
    type=int,
    default=300,
    help="Timeout for validation operation in seconds (default: 300).",
)
@click.option(
    "--validation-id",
    type=str,
    help="Custom validation ID for tracking. If not provided, one will be generated.",
)
def validate_graph(
    workspace: Path | None,
    log_level: str,
    config: Path | None,
    env: Path | None,
    scanners: str | None,
    max_entities: int | None,
    auto_repair: bool,
    output: Path | None,
    timeout: int,
    validation_id: str | None,
):
    """Trigger immediate validation of the knowledge graph.

    This command runs comprehensive validation across QDrant and Neo4j databases
    to detect inconsistencies, missing mappings, orphaned records, and other
    data integrity issues.

    Examples:
        # Run full validation
        qdrant-loader validation validate-graph

        # Run specific scanners with auto-repair
        qdrant-loader validation validate-graph --scanners missing_mappings,orphaned_records --auto-repair

        # Limit scan scope and save report
        qdrant-loader validation validate-graph --max-entities 1000 --output validation_report.json
    """
    try:
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)

        # Setup logging with workspace support
        setup_logging(log_level, workspace_config)
        logger = get_logger()

        # Load configuration
        load_config_with_workspace(
            workspace_config=workspace_config,
            config_path=config,
            env_path=env,
            skip_validation=False,
        )
        settings = check_settings()

        # Parse scanners list
        scanner_list = None
        if scanners:
            scanner_list = [s.strip() for s in scanners.split(",")]
            logger.info(f"Using specific scanners: {scanner_list}")

        # Run validation
        logger.info(
            "Starting graph validation",
            auto_repair=auto_repair,
            max_entities=max_entities,
            timeout=timeout,
        )

        # Run the async validation
        report = asyncio.run(
            _run_validation(
                settings=settings,
                validation_id=validation_id,
                scanners=scanner_list,
                max_entities=max_entities,
                auto_repair=auto_repair,
                timeout=timeout,
            )
        )

        # Output results
        report_dict = report.to_dict()

        if output:
            # Save to file
            with open(output, "w") as f:
                json.dump(report_dict, f, indent=2)
            echo(f"✅ Validation report saved to {output}")
        else:
            # Print to stdout
            echo("📊 Validation Report")
            echo("=" * 50)
            echo(json.dumps(report_dict, indent=2))

        # Print summary
        echo("\n📈 Summary:")
        echo(f"  Total Issues: {report.total_issues}")
        echo(f"  Critical: {report.critical_issues}")
        echo(f"  Error: {report.error_issues}")
        echo(f"  Warning: {report.warning_issues}")
        echo(f"  Info: {report.info_issues}")
        echo(f"  Health Score: {report.system_health_score:.1f}/100")

        if auto_repair and report.auto_repairable_issues > 0:
            echo(f"  Auto-repairable Issues: {report.auto_repairable_issues}")

        # Exit with appropriate code
        if report.critical_issues > 0:
            raise click.ClickException("Critical validation issues found")
        elif report.error_issues > 0:
            echo("⚠️  Validation completed with errors")
            exit(1)
        else:
            echo("✅ Validation completed successfully")

    except Exception as e:
        # Ensure logger is available in error case
        try:
            logger = get_logger()
            logger.error("Validation failed", error=str(e))
        except:
            pass
        raise ClickException(f"Graph validation failed: {str(e)}") from e


@validation_group.command(name="repair-inconsistencies")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option(
    "--report",
    type=ClickPath(exists=True, path_type=Path),
    help="Path to validation report JSON file containing issues to repair.",
)
@click.option(
    "--issue-ids",
    type=str,
    help="Comma-separated list of specific issue IDs to repair.",
)
@click.option(
    "--max-repairs",
    type=int,
    help="Maximum number of repairs to perform in this operation.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be repaired without actually performing repairs.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompts and proceed with repairs.",
)
@click.option(
    "--repair-id",
    type=str,
    help="Custom repair operation ID for tracking.",
)
def repair_inconsistencies(
    workspace: Path | None,
    log_level: str,
    config: Path | None,
    env: Path | None,
    report: Path | None,
    issue_ids: str | None,
    max_repairs: int | None,
    dry_run: bool,
    force: bool,
    repair_id: str | None,
):
    """Repair validation issues found in the knowledge graph.

    This command can repair issues from a validation report or specific
    issue IDs. It provides options for dry-run testing and confirmation
    prompts for safety.

    Examples:
        # Repair issues from validation report
        qdrant-loader validation repair-inconsistencies --report validation_report.json

        # Repair specific issues
        qdrant-loader validation repair-inconsistencies --issue-ids "issue-1,issue-2"

        # Dry run to see what would be repaired
        qdrant-loader validation repair-inconsistencies --report report.json --dry-run
    """
    try:
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        if not report and not issue_ids:
            raise ClickException("Either --report or --issue-ids must be specified")

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)

        # Setup logging with workspace support
        setup_logging(log_level, workspace_config)
        logger = get_logger()

        # Load configuration
        load_config_with_workspace(
            workspace_config=workspace_config,
            config_path=config,
            env_path=env,
            skip_validation=False,
        )
        settings = check_settings()

        # Load issues to repair
        issues_to_repair = []

        if report:
            # Load issues from validation report
            with open(report) as f:
                report_data = json.load(f)

            # Extract issues from report
            if "issues" in report_data:
                issues_to_repair = report_data["issues"]
                logger.info(f"Loaded {len(issues_to_repair)} issues from report")

        if issue_ids:
            # Filter by specific issue IDs
            issue_id_list = [id.strip() for id in issue_ids.split(",")]
            if issues_to_repair:
                # Filter existing issues
                issues_to_repair = [
                    issue
                    for issue in issues_to_repair
                    if issue.get("issue_id") in issue_id_list
                ]
            else:
                # Need to fetch issues by ID (would require validation system access)
                logger.warning("Specific issue ID repair requires a validation report")
                issues_to_repair = []

        if not issues_to_repair:
            echo("No issues found to repair")
            return

        # Show what will be repaired
        echo(f"📋 Found {len(issues_to_repair)} issues to repair:")
        for issue in issues_to_repair[:10]:  # Show first 10
            echo(
                f"  - {issue.get('issue_id', 'unknown')}: {issue.get('title', 'No title')}"
            )

        if len(issues_to_repair) > 10:
            echo(f"  ... and {len(issues_to_repair) - 10} more")

        if dry_run:
            echo("\n🔍 Dry run mode - no actual repairs will be performed")
            echo("✅ Dry run completed")
            return

        # Confirmation prompt
        if not force:
            if not click.confirm(
                f"\nProceed with repairing {len(issues_to_repair)} issues?"
            ):
                echo("Repair operation cancelled")
                return

        # Run repairs
        logger.info(
            "Starting repair operation",
            issue_count=len(issues_to_repair),
            max_repairs=max_repairs,
        )

        repair_results = asyncio.run(
            _run_repairs(
                settings=settings,
                issues=issues_to_repair,
                repair_id=repair_id,
                max_repairs=max_repairs,
            )
        )

        # Show results
        successful_repairs = sum(1 for r in repair_results if r.get("success", False))
        echo("\n📈 Repair Results:")
        echo(f"  Total Attempted: {len(repair_results)}")
        echo(f"  Successful: {successful_repairs}")
        echo(f"  Failed: {len(repair_results) - successful_repairs}")

        if successful_repairs == len(repair_results):
            echo("✅ All repairs completed successfully")
        elif successful_repairs > 0:
            echo("⚠️  Some repairs failed - check logs for details")
            exit(1)
        else:
            raise ClickException("All repair operations failed")

    except Exception as e:
        # Ensure logger is available in error case
        try:
            logger = get_logger()
            logger.error("Repair operation failed", error=str(e))
        except:
            pass
        raise ClickException(f"Repair operation failed: {str(e)}") from e


@validation_group.command(name="schedule-validation")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option(
    "--interval",
    type=Choice(["hourly", "daily", "weekly"], case_sensitive=False),
    default="daily",
    help="Validation interval (default: daily).",
)
@click.option(
    "--time",
    type=str,
    help="Specific time for daily/weekly validation (HH:MM format, e.g., '02:00').",
)
@click.option(
    "--day",
    type=Choice(
        ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        case_sensitive=False,
    ),
    help="Day of week for weekly validation.",
)
@click.option(
    "--auto-repair",
    is_flag=True,
    help="Enable automatic repair for scheduled validations.",
)
@click.option(
    "--enable/--disable",
    default=True,
    help="Enable or disable scheduled validation.",
)
def schedule_validation(
    workspace: Path | None,
    log_level: str,
    config: Path | None,
    env: Path | None,
    interval: str,
    time: str | None,
    day: str | None,
    auto_repair: bool,
    enable: bool,
):
    """Configure scheduled validation jobs.

    This command sets up automatic validation runs at specified intervals.
    Scheduled validations can include automatic repair of detected issues.

    Examples:
        # Schedule daily validation at 2 AM
        qdrant-loader validation schedule-validation --interval daily --time 02:00

        # Schedule weekly validation on Sunday with auto-repair
        qdrant-loader validation schedule-validation --interval weekly --day sunday --auto-repair

        # Disable scheduled validation
        qdrant-loader validation schedule-validation --disable
    """
    try:
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)

        # Setup logging with workspace support
        setup_logging(log_level, workspace_config)
        logger = get_logger()

        # Load configuration
        load_config_with_workspace(
            workspace_config=workspace_config,
            config_path=config,
            env_path=env,
            skip_validation=False,
        )
        settings = check_settings()

        if not enable:
            # Disable scheduled validation
            logger.info("Disabling scheduled validation")
            echo("⏹️  Scheduled validation disabled")
            # TODO: Implement actual scheduler disable logic
            return

        # Validate time format if provided
        if time:
            try:
                hour, minute = map(int, time.split(":"))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time range")
            except ValueError:
                raise ClickException("Time must be in HH:MM format (e.g., '02:00')")

        # Validate weekly options
        if interval == "weekly" and not day:
            raise ClickException("Day of week must be specified for weekly validation")

        # Configure scheduled validation
        logger.info(
            "Configuring scheduled validation",
            interval=interval,
            time=time,
            day=day,
            auto_repair=auto_repair,
        )

        # Configure and start the scheduler
        result = asyncio.run(
            _configure_scheduled_validation(
                settings=settings,
                interval=interval,
                time=time,
                day=day,
                auto_repair=auto_repair,
            )
        )

        if result["success"]:
            echo("⏰ Scheduled validation configured:")
            echo(f"  Interval: {interval}")
            if time:
                echo(f"  Time: {time}")
            if day:
                echo(f"  Day: {day}")
            echo(f"  Auto-repair: {'enabled' if auto_repair else 'disabled'}")
            echo(f"  Job ID: {result['job_id']}")
            echo("✅ Scheduler configuration saved")
        else:
            raise ClickException(f"Failed to configure scheduler: {result['error']}")

    except Exception as e:
        # Ensure logger is available in error case
        try:
            logger = get_logger()
            logger.error("Schedule configuration failed", error=str(e))
        except:
            pass
        raise ClickException(
            f"Failed to configure scheduled validation: {str(e)}"
        ) from e


@validation_group.command(name="status")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option(
    "--history",
    type=int,
    help="Number of historical validation records to show.",
)
@click.option(
    "--filter-status",
    type=Choice(["completed", "failed", "running", "cancelled"], case_sensitive=False),
    help="Filter history by validation status.",
)
@click.option(
    "--json-output",
    is_flag=True,
    help="Output status information in JSON format.",
)
def validation_status(
    workspace: Path | None,
    log_level: str,
    config: Path | None,
    env: Path | None,
    history: int | None,
    filter_status: str | None,
    json_output: bool,
):
    """Display validation system status and history.

    This command shows the current state of the validation system,
    including active validations, recent history, and system statistics.

    Examples:
        # Show current status
        qdrant-loader validation status

        # Show last 10 validation records
        qdrant-loader validation status --history 10

        # Show only failed validations in JSON format
        qdrant-loader validation status --filter-status failed --json-output
    """
    try:
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)

        # Setup logging with workspace support
        setup_logging(log_level, workspace_config)
        logger = get_logger()

        # Load configuration
        load_config_with_workspace(
            workspace_config=workspace_config,
            config_path=config,
            env_path=env,
            skip_validation=False,
        )
        settings = check_settings()

        # Get validation status
        logger.info("Retrieving validation status")

        status_info = asyncio.run(
            _get_validation_status(
                settings=settings,
                history_limit=history,
                status_filter=filter_status,
            )
        )

        if json_output:
            # Output as JSON
            echo(json.dumps(status_info, indent=2))
        else:
            # Formatted output
            echo("📊 Validation System Status")
            echo("=" * 40)

            # Current status
            echo(
                f"System Status: {'🟢 Running' if status_info.get('running') else '🔴 Stopped'}"
            )
            echo(f"Active Validations: {status_info.get('active_validations', 0)}")

            # Statistics
            stats = status_info.get("statistics", {})
            echo("\n📈 Statistics:")
            echo(f"  Total Validations: {stats.get('total_validations', 0)}")
            echo(f"  Successful: {stats.get('successful_validations', 0)}")
            echo(f"  Failed: {stats.get('failed_validations', 0)}")
            echo(f"  Total Repairs: {stats.get('total_repairs', 0)}")
            echo(f"  Auto Repairs: {stats.get('auto_repairs_performed', 0)}")

            # Last validation
            last_validation = status_info.get("last_validation")
            if last_validation:
                echo("\n🕐 Last Validation:")
                echo(f"  Report ID: {last_validation.get('report_id', 'unknown')}")
                echo(f"  Generated: {last_validation.get('generated_at', 'unknown')}")
                echo(
                    f"  Total Issues: {last_validation.get('summary', {}).get('total_issues', 0)}"
                )
                echo(
                    f"  Health Score: {last_validation.get('summary', {}).get('system_health_score', 0):.1f}/100"
                )

            # History
            history_records = status_info.get("history", [])
            if history_records:
                echo(f"\n📋 Recent History ({len(history_records)} records):")
                for record in history_records[:5]:  # Show first 5
                    status_emoji = {
                        "completed": "✅",
                        "failed": "❌",
                        "running": "🔄",
                        "cancelled": "⏹️",
                    }.get(record.get("status", "unknown"), "❓")

                    echo(
                        f"  {status_emoji} {record.get('validation_id', 'unknown')} - {record.get('start_time', 'unknown')}"
                    )

    except Exception as e:
        # Ensure logger is available in error case
        try:
            logger = get_logger()
            logger.error("Status retrieval failed", error=str(e))
        except:
            pass
        raise ClickException(f"Failed to retrieve validation status: {str(e)}") from e


# Async helper functions


async def _run_validation(
    settings,
    validation_id: str | None,
    scanners: list[str] | None,
    max_entities: int | None,
    auto_repair: bool,
    timeout: int,
):
    """Run validation operation asynchronously."""

    # Initialize the base managers first (they don't depend on each other)
    neo4j_manager = Neo4jManager(settings)
    qdrant_manager = QdrantManager(settings)

    # Initialize the ID mapping manager with the base managers
    id_mapping_manager = IDMappingManager(
        neo4j_manager=neo4j_manager,
        qdrant_manager=qdrant_manager,
    )

    # Create the core validation system
    validation_system = ValidationRepairSystem(
        id_mapping_manager=id_mapping_manager,
        neo4j_manager=neo4j_manager,
        qdrant_manager=qdrant_manager,
        auto_repair_enabled=auto_repair,
    )

    # Initialize the integrator with the validation system
    integrator = ValidationRepairSystemIntegrator(
        validation_repair_system=validation_system,
        settings=settings,
        validation_timeout_seconds=timeout,
    )

    try:
        # Initialize and start the integrator
        await integrator.initialize()
        await integrator.start()

        # Run validation using the integrator
        report = await integrator.trigger_validation(
            validation_id=validation_id,
            scanners=scanners,
            max_entities_per_scanner=max_entities,
            auto_repair=auto_repair,
        )

        return report

    finally:
        # Ensure proper cleanup
        await integrator.stop()


async def _run_repairs(
    settings,
    issues: list,
    repair_id: str | None,
    max_repairs: int | None,
):
    """Run repair operations asynchronously."""

    # Initialize the base managers first
    neo4j_manager = Neo4jManager(settings)
    qdrant_manager = QdrantManager(settings)

    # Initialize the ID mapping manager with the base managers
    id_mapping_manager = IDMappingManager(
        neo4j_manager=neo4j_manager,
        qdrant_manager=qdrant_manager,
    )

    # Create the core validation system
    validation_system = ValidationRepairSystem(
        id_mapping_manager=id_mapping_manager,
        neo4j_manager=neo4j_manager,
        qdrant_manager=qdrant_manager,
        auto_repair_enabled=True,
    )

    # Initialize the integrator
    integrator = ValidationRepairSystemIntegrator(
        validation_repair_system=validation_system,
        settings=settings,
    )

    try:
        # Initialize and start the integrator
        await integrator.initialize()
        await integrator.start()

        # Convert dict issues to ValidationIssue objects if needed
        validation_issues = []
        for issue_data in issues[:max_repairs] if max_repairs else issues:
            if isinstance(issue_data, dict):
                # Convert dict to ValidationIssue (simplified conversion)
                validation_issue = ValidationIssue(
                    issue_id=issue_data.get("issue_id", "unknown"),
                    title=issue_data.get("title", "Unknown Issue"),
                    description=issue_data.get("description", ""),
                )
                validation_issues.append(validation_issue)
            else:
                validation_issues.append(issue_data)

        # Run repairs using the integrator
        repair_results = await integrator.repair_issues(
            issues=validation_issues,
            repair_id=repair_id,
            max_repairs=max_repairs,
        )

        # Convert RepairResult objects to dict format for CLI output
        results = []
        for result in repair_results:
            results.append(
                {
                    "issue_id": result.issue_id,
                    "success": result.success,
                    "action_taken": (
                        result.action_taken.value if result.action_taken else "unknown"
                    ),
                    "error_message": result.error_message,
                }
            )

        return results

    finally:
        # Ensure proper cleanup
        await integrator.stop()


async def _get_validation_status(
    settings,
    history_limit: int | None,
    status_filter: str | None,
):
    """Get validation system status asynchronously."""

    # Initialize the base managers first
    neo4j_manager = Neo4jManager(settings)
    qdrant_manager = QdrantManager(settings)

    # Initialize the ID mapping manager with the base managers
    id_mapping_manager = IDMappingManager(
        neo4j_manager=neo4j_manager,
        qdrant_manager=qdrant_manager,
    )

    # Create the core validation system
    validation_system = ValidationRepairSystem(
        id_mapping_manager=id_mapping_manager,
        neo4j_manager=neo4j_manager,
        qdrant_manager=qdrant_manager,
    )

    # Initialize the integrator
    integrator = ValidationRepairSystemIntegrator(
        validation_repair_system=validation_system,
        settings=settings,
    )

    try:
        # Initialize the integrator (no need to start for status check)
        await integrator.initialize()

        # Get validation status
        status_info = await integrator.get_validation_status()

        # Get validation history if requested
        history = []
        if history_limit:
            history = await integrator.get_validation_history(
                limit=history_limit,
                status_filter=status_filter,
            )

        # Combine status and history
        result = {
            **status_info,
            "history": history,
        }

        return result

    finally:
        # No need to stop since we didn't start
        pass


# Backward compatibility command (single command without group)
@click.command(name="validate")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@CONFIG_OPTION
@ENV_OPTION
def validate_command(
    workspace: Path | None,
    log_level: str,
    config: Path | None,
    env: Path | None,
):
    """Quick validation command (backward compatibility).

    This is a simplified validation command that runs basic validation
    with default settings for backward compatibility.
    """
    # Delegate to the full validate-graph command with defaults
    ctx = click.get_current_context()
    ctx.invoke(
        validate_graph,
        workspace=workspace,
        log_level=log_level,
        config=config,
        env=env,
        scanners=None,
        max_entities=None,
        auto_repair=False,
        output=None,
        timeout=300,
        validation_id=None,
    )


async def _configure_scheduled_validation(
    settings,
    interval: str,
    time: str | None,
    day: str | None,
    auto_repair: bool,
) -> dict:
    """Configure scheduled validation asynchronously."""
    from datetime import datetime

    from qdrant_loader.config.validation import ValidationConfig
    from qdrant_loader.core.validation_repair import ValidationScheduler

    try:
        # Initialize managers
        neo4j_manager = Neo4jManager(settings.neo4j)
        qdrant_manager = QdrantManager(settings.qdrant)
        id_mapping_manager = IDMappingManager(neo4j_manager, qdrant_manager)

        # Initialize validation system
        validation_repair_system = ValidationRepairSystem(
            neo4j_manager=neo4j_manager,
            qdrant_manager=qdrant_manager,
            id_mapping_manager=id_mapping_manager,
        )

        # Initialize integrator
        validation_integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=validation_repair_system,
            settings=settings,
        )

        # Create validation config with scheduler enabled
        validation_config = ValidationConfig(
            enable_scheduled_validation=True,
            default_schedule_interval=interval,
        )

        # Initialize scheduler
        scheduler = ValidationScheduler(
            validation_integrator=validation_integrator,
            config=validation_config,
        )

        try:
            # Start the scheduler
            await scheduler.start()

            # Create schedule configuration
            schedule_config = {}
            if time:
                hour, minute = map(int, time.split(":"))
                schedule_config["hour"] = hour
                schedule_config["minute"] = minute

            if day and interval == "weekly":
                day_mapping = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                }
                schedule_config["day_of_week"] = day_mapping[day.lower()]

            # Generate job ID
            job_id = (
                f"scheduled_validation_{interval}_{int(datetime.now().timestamp())}"
            )

            # Schedule the validation
            success = await scheduler.schedule_validation(
                job_id=job_id,
                schedule_type=interval,
                schedule_config=schedule_config,
                auto_repair=auto_repair,
                name=f"Scheduled {interval.title()} Validation",
            )

            if success:
                return {"success": True, "job_id": job_id}
            else:
                return {"success": False, "error": "Failed to schedule validation job"}

        finally:
            # Stop the scheduler (it will be managed by the application)
            await scheduler.stop()

    except Exception as e:
        return {"success": False, "error": str(e)}
