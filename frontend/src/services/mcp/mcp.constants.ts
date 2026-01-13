export const SERVER_TYPES = {
  http: {
    label: 'HTTP Server',
    description: 'Remote MCP server via HTTP/HTTPS',
    badgeColor: 'bg-blue-500/10 text-blue-700 border-blue-500/20 dark:bg-blue-500/20 dark:text-blue-400',
    needsUrl: true,
    needsAuth: true,
    autoInstall: false,
    example: {
      url: 'https://mcp.example.com',
      auth_type: 'api-key'
    }
  },
  npx: {
    label: 'npx (Node.js)',
    description: 'Auto-installs packages from npm',
    badgeColor: 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20 dark:bg-emerald-500/20 dark:text-emerald-400',
    autoInstall: true,
    argsPlaceholder: '-y @modelcontextprotocol/server-github',
    example: {
      args: ['-y', '@modelcontextprotocol/server-github'],
      env: { GITHUB_PERSONAL_ACCESS_TOKEN: 'ghp_xxx' }
    }
  },
  uvx: {
    label: 'uvx (Python)',
    description: 'Auto-installs packages from PyPI',
    badgeColor: 'bg-purple-500/10 text-purple-700 border-purple-500/20 dark:bg-purple-500/20 dark:text-purple-400',
    autoInstall: true,
    prerequisite: 'pip install uv',
    argsPlaceholder: 'mcp-server-sqlite --db-path ./data.db',
    example: {
      args: ['mcp-server-sqlite', '--db-path', './data.db'],
      env: {}
    }
  },
  docker: {
    label: 'Docker',
    description: 'Runs in isolated container (auto-pulls image)',
    badgeColor: 'bg-cyan-500/10 text-cyan-700 border-cyan-500/20 dark:bg-cyan-500/20 dark:text-cyan-400',
    autoInstall: true,
    prerequisite: 'Docker Desktop',
    argsPlaceholder: 'ghcr.io/github/github-mcp-server',
    example: {
      args: ['ghcr.io/github/github-mcp-server'],
      env: { GITHUB_PERSONAL_ACCESS_TOKEN: 'ghp_xxx' }
    }
  }
} as const

export type ServerTypeKey = keyof typeof SERVER_TYPES

// Common MCP server configurations for quick import
export const COMMON_MCP_SERVERS = {
  github: {
    name: 'GitHub',
    type: 'npx' as const,
    description: 'Access GitHub repositories, issues, and pull requests',
    args: ['-y', '@modelcontextprotocol/server-github'],
    env: { GITHUB_PERSONAL_ACCESS_TOKEN: '${GITHUB_TOKEN}' }
  },
  filesystem: {
    name: 'Filesystem',
    type: 'npx' as const,
    description: 'Access and manage local filesystem',
    args: ['-y', '@modelcontextprotocol/server-filesystem', '${HOME}/projects'],
    env: {}
  },
  sqlite: {
    name: 'SQLite',
    type: 'uvx' as const,
    description: 'Query and manage SQLite databases',
    args: ['mcp-server-sqlite', '--db-path', './data/app.db'],
    env: {}
  },
  fetch: {
    name: 'Web Fetch',
    type: 'npx' as const,
    description: 'Fetch and process web content',
    args: ['-y', '@modelcontextprotocol/server-fetch'],
    env: { USER_AGENT: 'MyApp/1.0' }
  },
  context7: {
    name: 'Context7 (Upstash)',
    type: 'npx' as const,
    description: 'Vector search with Upstash',
    args: ['-y', '@upstash/context7-mcp'],
    env: {
      UPSTASH_VECTOR_REST_URL: '${UPSTASH_URL}',
      UPSTASH_VECTOR_REST_TOKEN: '${UPSTASH_TOKEN}'
    }
  }
}

// Example JSON configuration for import
export const EXAMPLE_JSON_CONFIG = {
  mcpServers: {
    github: {
      type: 'npx',
      args: ['-y', '@modelcontextprotocol/server-github'],
      env: {
        GITHUB_PERSONAL_ACCESS_TOKEN: '${GITHUB_TOKEN}'
      }
    },
    'python-sqlite': {
      type: 'uvx',
      args: ['mcp-server-sqlite', '--db-path', './data/app.db']
    },
    'python-fetch': {
      type: 'npx',
      args: ['-y', '@modelcontextprotocol/server-fetch'],
      env: {
        USER_AGENT: 'MyApp/1.0'
      }
    },
    filesystem: {
      type: 'npx',
      args: ['-y', '@modelcontextprotocol/server-filesystem', '${HOME}/projects']
    },
    context7: {
      type: 'npx',
      args: ['-y', '@upstash/context7-mcp'],
      env: {
        UPSTASH_VECTOR_REST_URL: '${UPSTASH_URL}',
        UPSTASH_VECTOR_REST_TOKEN: '${UPSTASH_TOKEN}'
      }
    }
  }
}

// Status colors for UI
export const STATUS_CONFIG = {
  active: {
    color: 'green',
    label: 'Active',
    description: 'Server is operational'
  },
  pending: {
    color: 'gray',
    label: 'Pending',
    description: 'Awaiting verification'
  },
  pending_authorization: {
    color: 'yellow',
    label: 'Pending OAuth',
    description: 'OAuth authorization required'
  },
  failed: {
    color: 'red',
    label: 'Failed',
    description: 'Authentication error'
  },
  unreachable: {
    color: 'red',
    label: 'Unreachable',
    description: 'Server is unreachable'
  }
} as const

// Auth types for HTTP servers
export const AUTH_TYPES = {
  'api-key': {
    label: 'API Key',
    description: 'Authenticate with an API key',
    requiresKey: true
  },
  oauth: {
    label: 'OAuth',
    description: 'Authenticate with OAuth 2.0',
    requiresKey: false
  },
  none: {
    label: 'No Authentication',
    description: 'No authentication required',
    requiresKey: false
  }
} as const
