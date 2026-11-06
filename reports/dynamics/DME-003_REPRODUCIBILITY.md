# Reproduce DME-003

Use Python3.12 and the pinned lock. From the distribution root:

    python -m dynamics.cli run DME-003 --data /your/local/dynamics-data
    python -m dynamics.cli reproduce JOB_UUID --data /your/local/dynamics-data

The second command rehashes every acquired source object, reparses original selected ZIP bytes and recomputes mathematical results offline, with the original manifest parameters. Missing or altered cached bytes fail explicitly; a new download is a new acquisition, not substitution for an old vintage. The results_sha256 excludes measured execution timing but includes all scientific results and source identities. Public source packages do not contain multi-GB third-party archives. Dataset source availability may change. All seeds/parameters/dependency versions and source hashes are in the manifest.
