This proof of concept implements a minimal Flask API that accepts async 'operation' logs,
stores them in a JSON file, and simulates syncing to a central database or other nodes.

What’s missing from the full vision includes multi-node networking, strong conflict
resolution, authentication/authorization, offline import/export, robust retries,
and the operational requirements (monitoring, auditing, high availability).
