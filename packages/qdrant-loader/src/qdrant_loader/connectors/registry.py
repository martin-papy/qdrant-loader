from qdrant_loader.connectors.confluence.config import ConfluenceDeploymentType
from qdrant_loader.connectors.confluence.connector import ConfluenceConnector
from qdrant_loader.connectors.git.connector import GitConnector
from qdrant_loader.connectors.jira.cloud_connector import JiraCloudConnector
from qdrant_loader.connectors.jira.config import JiraDeploymentType
from qdrant_loader.connectors.jira.data_center_connector import JiraDataCenterConnector
from qdrant_loader.connectors.localfile.connector import LocalFileConnector
from qdrant_loader.connectors.publicdocs.connector import PublicDocsConnector

CONNECTOR_REGISTRY = {
    ("confluence", ConfluenceDeploymentType.CLOUD): ConfluenceConnector,
    ("confluence", ConfluenceDeploymentType.DATACENTER): ConfluenceConnector,
    ("git", None): GitConnector,
    ("jira", JiraDeploymentType.CLOUD): JiraCloudConnector,
    ("jira", JiraDeploymentType.DATACENTER): JiraDataCenterConnector,
    ("publicdocs", None): PublicDocsConnector,
    ("localfile", None): LocalFileConnector,
}
