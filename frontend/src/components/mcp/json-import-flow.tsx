"use client"

import { useState } from "react"
import { FileJson, AlertCircle, CheckCircle2, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ServerSelectionTree } from "./server-selection-tree"
import type { MCPServerType } from "@/services/mcp/mcp.types"

interface ParsedServer {
  id: string
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

interface JSONImportFlowProps {
  onImport: (servers: ParsedServer[]) => void
}

export function JSONImportFlow({ onImport }: JSONImportFlowProps) {
  const [jsonInput, setJsonInput] = useState("")
  const [parsedServers, setParsedServers] = useState<ParsedServer[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [envVariables, setEnvVariables] = useState<EnvVariable[]>([])
  const [parseError, setParseError] = useState<string | null>(null)
  const [step, setStep] = useState<"input" | "selection" | "env">("input")

  const extractEnvVariables = (servers: ParsedServer[]): EnvVariable[] => {
    const variables = new Map<string, string>()

    servers.forEach(server => {
      if (server.env) {
        Object.entries(server.env).forEach(([key, value]) => {
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
        let type: MCPServerType = 'http'
        let command = config.command

        // LOG #1 - Parsing du JSON
        console.log('🔹 [JSON PARSING] Server:', {
          key: name,
          name: name,
          type: config.type,
          command: config.command,
          args: config.args,
          argsLength: config.args?.length,
          hasEnv: !!config.env
        })

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
          id: `${name}-${Date.now()}`,
          name,
          type,
          command,
          args: config.args || [],
          env: config.env || {}
        })
      })

      // LOG #2 - Serveurs parsés
      console.log('🔹 [JSON PARSING] Final parsed servers:', servers)

      setParsedServers(servers)
      setSelectedIds(servers.map(s => s.id))
      const vars = extractEnvVariables(servers)
      setEnvVariables(vars)
      setParseError(null)

      if (servers.length === 1 && vars.length === 0) {
        handleFinalImport(servers, [])
      } else if (servers.length === 1) {
        setStep("env")
      } else {
        setStep("selection")
      }
    } catch (error) {
      setParseError(`Erreur de parsing JSON : ${error instanceof Error ? error.message : 'Format invalide'}`)
    }
  }

  const handleContinueToEnv = () => {
    const selectedServers = parsedServers.filter(s => selectedIds.includes(s.id))
    const vars = extractEnvVariables(selectedServers)
    setEnvVariables(vars)

    if (vars.length === 0) {
      handleFinalImport(selectedServers, [])
    } else {
      setStep("env")
    }
  }

  const handleFinalImport = (servers?: ParsedServer[], vars?: EnvVariable[]) => {
    const serversToImport = servers || parsedServers.filter(s => selectedIds.includes(s.id))
    const variablesToUse = vars || envVariables

    const envMap = new Map<string, string>()
    variablesToUse.forEach(v => {
      envMap.set(v.key, v.value)
    })

    const finalServers = serversToImport.map(server => {
      const env: Record<string, string> = {}

      if (server.env) {
        Object.entries(server.env).forEach(([key, value]) => {
          let finalValue = value
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
        ...server,
        env
      }
    })

    // LOG #3 - Envoi vers modal
    console.log('🔹 [JSON IMPORT] Sending to modal.handleJSONImport:', finalServers.map(s => ({
      name: s.name,
      type: s.type,
      argsLength: s.args?.length,
      args: s.args
    })))

    onImport(finalServers)
  }

  const handleReset = () => {
    setJsonInput("")
    setParsedServers([])
    setSelectedIds([])
    setEnvVariables([])
    setParseError(null)
    setStep("input")
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
    }
  }
}`

  return (
    <div className="space-y-4">
      {/* Step 1: Input */}
      {step === "input" && (
        <>
          <div className="space-y-2">
            <Label htmlFor="json-input">Configuration JSON</Label>
            <Textarea
              id="json-input"
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
              placeholder={exampleJSON}
              rows={12}
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
              <li>Utilisez <code className="bg-background px-1 rounded">{`\${VARIABLE}`}</code> pour les valeurs sensibles</li>
            </ul>
          </div>

          <Button type="button" onClick={handleParse} disabled={!jsonInput.trim()} className="w-full">
            <FileJson className="size-4 mr-2" />
            Analyser
          </Button>
        </>
      )}

      {/* Step 2: Selection */}
      {step === "selection" && (
        <>
          <div className="flex items-center gap-2 p-3 bg-green-500/10 text-green-700 dark:text-green-400 rounded-lg">
            <CheckCircle2 className="size-4 flex-shrink-0" />
            <p className="text-sm">
              {parsedServers.length} serveur{parsedServers.length > 1 ? 's' : ''} détecté{parsedServers.length > 1 ? 's' : ''}
            </p>
          </div>

          <div className="space-y-2">
            <Label>Sélectionner les serveurs à importer</Label>
            <ServerSelectionTree
              servers={parsedServers}
              selectedIds={selectedIds}
              onToggle={(id, selected) => {
                setSelectedIds(prev =>
                  selected
                    ? [...prev, id]
                    : prev.filter(sid => sid !== id)
                )
              }}
            />
          </div>

          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={handleReset} className="flex-1">
              <ArrowLeft className="size-4 mr-2" />
              Retour
            </Button>
            <Button
              type="button"
              onClick={handleContinueToEnv}
              disabled={selectedIds.length === 0}
              className="flex-1"
            >
              Continuer ({selectedIds.length})
            </Button>
          </div>
        </>
      )}

      {/* Step 3: Environment Variables */}
      {step === "env" && (
        <>
          <div className="flex items-center gap-2 p-3 bg-blue-500/10 text-blue-700 dark:text-blue-400 rounded-lg">
            <CheckCircle2 className="size-4 flex-shrink-0" />
            <p className="text-sm">
              {selectedIds.length} serveur{selectedIds.length > 1 ? 's' : ''} sélectionné{selectedIds.length > 1 ? 's' : ''}
            </p>
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
                      <code className="bg-muted px-1.5 py-0.5 rounded">{`\${${envVar.key}}`}</code>
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

          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setStep(parsedServers.length > 1 ? "selection" : "input")}
              className="flex-1"
            >
              <ArrowLeft className="size-4 mr-2" />
              Retour
            </Button>
            <Button
              type="button"
              onClick={() => handleFinalImport()}
              disabled={envVariables.some(v => !v.value.trim())}
              className="flex-1"
            >
              Importer {selectedIds.length} serveur{selectedIds.length > 1 ? 's' : ''}
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
