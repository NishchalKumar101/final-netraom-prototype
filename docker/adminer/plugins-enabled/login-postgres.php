<?php

/**
 * Force PostgreSQL driver for Docker Compose (avoids MySQL "Connection refused" on server=postgres).
 * @see https://www.adminer.org/plugins/#use
 */
require_once __DIR__ . '/../plugins/login-servers.php';

return new AdminerLoginServers([
    'postgres' => [
        'server' => 'postgres',
        'driver' => 'pgsql',
    ],
]);
