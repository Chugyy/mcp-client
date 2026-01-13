"use client"

import { useState } from "react"
import { FileJson, AlertCircle, CheckCircle2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import type { CreateMCPServerDTO, MCPServerType } from "@/services/mcp/mcp.types"

interface ParsedServer {
  name: string
  type: MCPServerType
  command?: string
  args?: string[]
  env?: Record<string, string>
}

interface EnvVariable {
  key: string
  placeholder: string
  value: string
}

interface JSONImporterProps {
  open: boolean
  onClose: () => void
  onImport: (servers: CreateMCPServerDTO[]) => void
}

export function JSONImporter({ open, onClose, onImport }: JSONImporterProps) {
  const [jsonInput, setJsonInput] = useState("")
  const [parsedServers, setParsedServers] = useState<ParsedServer[]>([])
  const [envVariables, setEnvVariables] = useState<EnvVariable[]>([])
  const [parseError, setParseError] = useState<string | null>(null)
  const [step, setStep] = useState<"input" | "env">("input")

  const extractEnvVariables = (servers: ParsedServer[]): EnvVariable[] => {
    const variables = new Map<string, string>()

    servers.forEach(server => {
      if (server.env) {
        Object.entries(server.env).forEach(([key, value]) => {
          // Detect ${VARIABLE_NAME} patterns
          const matches = value.matchAll(/\$\{([A-Z_][A-Z0-9_]*)\}/g)
          for (const match of matches) {
            const varName = match[1]
            if (!variables.has(varName)) {
              variables.set(varName, value)
            }
          }
        })
      }
    })

    return Array.from(variables.entries()).map(([key, placeholder]) => ({
      key,
      placeholder,
      value: ""
    }))
  }

  const handleParse = () => {
    try {
      const parsed = JSON.parse(jsonInput)

      if (!parsed.mcpServers || typeof parsed.mcpServers !== 'object') {
        setParseError("Format invalide : l'objet 'mcpServers' est requis")
        return
      }

      const servers: ParsedServer[] = []

      Object.entries(parsed.mcpServers).forEach(([name, config]: [string, any]) => {
        // Determine type from config
        let type: MCPServerType = 'http'
        let command = config.command

        // Déterminer le type
        if (config.type && ['http', 'npx', 'uvx', 'docker'].includes(config.type)) {
          // Type valide fourni
          type = config.type
        } else if (config.type === 'stdio') {
          // Ancien format "stdio" → inférer depuis command
          if (command === 'npx') type = 'npx'
          else if (command === 'uvx') type = 'uvx'
          else if (command === 'docker') type = 'docker'
          else if (command === 'python') type = 'npx'
          else type = 'npx' // Par défaut npx pour stdio
        } else if (command) {
          // Pas de type, inférer depuis command
          if (command === 'npx') type = 'npx'
          else if (command === 'uvx') type = 'uvx'
          else if (command === 'docker') type = 'docker'
          else if (command === 'python') type = 'npx'
        } else {
          // Aucun type ni command → défaut npx
          type = 'npx'
        }

        servers.push({
          name,
          type,
          command,
          args: config.args || [],
          env: config.env || {}
        })
      })

      setParsedServers(servers)
      const vars = extractEnvVariables(servers)
      setEnvVariables(vars)
      setParseError(null)

      // If no env variables needed, go directly to import
      if (vars.length === 0) {
        handleImport(servers, [])
      } else {
        setStep("env")
      }
    } catch (error) {
      setParseError(`Erreur de parsing JSON : ${error instanceof Error ? error.message : 'Format invalide'}`)
    }
  }

  const handleImport = (servers?: ParsedServer[], vars?: EnvVariable[]) => {
    const serversToImport = servers || parsedServers
    const variablesToUse = vars || envVariables

    // Build env variables map
    const envMap = new Map<string, string>()
    variablesToUse.forEach(v => {
      envMap.set(v.key, v.value)
    })

    // Replace ${VAR} with actual values
    const finalServers: CreateMCPServerDTO[] = serversToImport.map(server => {
      const env: Record<string, string> = {}

      if (server.env) {
        Object.entries(server.env).forEach(([key, value]) => {
          let finalValue = value
          // Replace all ${VAR_NAME} with actual values
          const matches = value.matchAll(/\$\{([A-Z_][A-Z0-9_]*)\}/g)
          for (const match of matches) {
            const varName = match[1]
            const actualValue = envMap.get(varName) || ""
            finalValue = finalValue.replace(`\${${varName}}`, actualValue)
          }
          env[key] = finalValue
        })
      }

      return {
        name: server.name,
        type: server.type,
        args: server.args || [],
        env,
        enabled: true
      }
    })

    onImport(finalServers)
    handleReset()
  }

  const handleReset = () => {
    setJsonInput("")
    setParsedServers([])
    setEnvVariables([])
    setParseError(null)
    setStep("input")
    onClose()
  }

  const updateEnvValue = (key: string, value: string) => {
    setEnvVariables(prev =>
      prev.map(v => v.key === key ? { ...v, value } : v)
    )
  }

  const exampleJSON = `{
  "mcpServers": {
    "github": {
      "type": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "\${GITHUB_TOKEN}"
      }
    },
    "sqlite": {
      "type": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "./data/app.db"]
    },
    "filesystem": {
      "type": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "\${HOME}/projects"]
    }
  }
}`

  return (
    <Dialog open={open} onOpenChange={handleReset}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileJson className="size-5" />
            Importer une configuration JSON
          </DialogTitle>
          <DialogDescription>
            Collez votre configuration MCP au format JSON pour créer plusieurs serveurs automatiquement
          </DialogDescription>
        </DialogHeader>

        {step === "input" && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="json-input">Configuration JSON</Label>
              <Textarea
                id="json-input"
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                placeholder={exampleJSON}
                rows={16}
                className="font-mono text-xs"
              />
            </div>

            {parseError && (
              <div className="flex items-start gap-2 p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
                <AlertCircle className="size-4 mt-0.5 flex-shrink-0" />
                <p>{parseError}</p>
              </div>
            )}

            <div className="p-3 bg-muted rounded-lg text-xs space-y-2">
              <p className="font-medium">Format attendu :</p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                <li>Objet racine avec clé <code className="bg-background px-1 rounded">mcpServers</code></li>
                <li>Chaque serveur a un <code className="bg-background px-1 rounded">type</code> (npx, uvx, docker, http)</li>
                <li>Arguments dans <code className="bg-background px-1 rounded">args</code> (array)</li>
                <li>Variables d'environnement dans <code className="bg-background px-1 rounded">env</code> (object)</li>
                <li>Utilisez <code className="bg-background px-1 rounded">${`\${VARIABLE}`}</code> pour les valeurs sensibles</li>
              </ul>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleReset}>
                Annuler
              </Button>
              <Button onClick={handleParse} disabled={!jsonInput.trim()}>
                Analyser
              </Button>
            </DialogFooter>
          </div>
        )}

        {step === "env" && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 p-3 bg-green-500/10 text-green-700 dark:text-green-400 rounded-lg">
              <CheckCircle2 className="size-4 flex-shrink-0" />
              <p className="text-sm">
                {parsedServers.length} serveur{parsedServers.length > 1 ? 's' : ''} détecté{parsedServers.length > 1 ? 's' : ''}
              </p>
            </div>

            <div className="space-y-3">
              <Label>Serveurs à créer</Label>
              <div className="space-y-2">
                {parsedServers.map((server, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 bg-muted rounded">
                    <Badge variant="outline">{server.type.toUpperCase()}</Badge>
                    <span className="font-medium">{server.name}</span>
                    <span className="text-xs text-muted-foreground truncate">
                      {server.args?.join(' ')}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {envVariables.length > 0 && (
              <div className="space-y-3">
                <Label>Variables d'environnement détectées</Label>
                <p className="text-xs text-muted-foreground">
                  Renseignez les valeurs sensibles pour remplacer les variables
                </p>
                <div className="space-y-3">
                  {envVariables.map((envVar) => (
                    <div key={envVar.key} className="space-y-2">
                      <Label htmlFor={`env-${envVar.key}`} className="text-xs">
                        <code className="bg-muted px-1.5 py-0.5 rounded">${`\${${envVar.key}}`}</code>
                      </Label>
                      <Input
                        id={`env-${envVar.key}`}
                        type="password"
                        value={envVar.value}
                        onChange={(e) => updateEnvValue(envVar.key, e.target.value)}
                        placeholder={`Valeur pour ${envVar.key}`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setStep("input")}>
                Retour
              </Button>
              <Button
                onClick={() => handleImport()}
                disabled={envVariables.some(v => !v.value.trim())}
              >
                Importer {parsedServers.length} serveur{parsedServers.length > 1 ? 's' : ''}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
