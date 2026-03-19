(function () {
    if (window.__qdrantHotReloadInitialized) {
        return;
    }
    window.__qdrantHotReloadInitialized = true;

    // Hot reload should only run in local development servers.
    var host = window.location.hostname;
    if (host !== "127.0.0.1" && host !== "localhost") {
        return;
    }

    var currentVersion = Number(window.__qdrantHotReloadVersion || 0);

    function pollForReload() {
        fetch("/__reload", { cache: "no-store" })
            .then(function (response) {
                if (!response.ok) {
                    return null;
                }
                return response.text();
            })
            .then(function (versionText) {
                if (versionText === null) {
                    return;
                }

                var nextVersion = Number(versionText);
                if (!Number.isFinite(nextVersion)) {
                    return;
                }

                if (nextVersion > currentVersion) {
                    currentVersion = nextVersion;
                    window.location.reload();
                }
            })
            .catch(function () {
                // Ignore transient network errors while polling.
            });
    }

    pollForReload();
    window.setInterval(pollForReload, 1000);
})();
