"use client"

import { useState, useMemo } from "react"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { ExecutionLog } from "@/services/automations/automations.types"
import { Search, Info, AlertTriangle, XCircle } from "lucide-react"

interface ExecutionLogsViewerProps {
  logs: ExecutionLog[]
}

export function ExecutionLogsViewer({ logs }: ExecutionLogsViewerProps) {
  const [levelFilter, setLevelFilter] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState('')

  // Filtrage des logs
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchesLevel = levelFilter === 'ALL' || log.level === levelFilter
      const matchesSearch =
        searchQuery === '' ||
        log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.step_name.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesLevel && matchesSearch
    })
  }, [logs, levelFilter, searchQuery])

  // Configuration des niveaux
  const getLevelConfig = (level: ExecutionLog['level']) => {
    switch (level) {
      case 'INFO':
        return {
          icon: <Info className="size-4 text-blue-600 dark:text-blue-400" />,
          className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
        }
      case 'WARNING':
        return {
          icon: <AlertTriangle className="size-4 text-orange-600 dark:text-orange-400" />,
          className: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
        }
      case 'ERROR':
        return {
          icon: <XCircle className="size-4 text-red-600 dark:text-red-400" />,
          className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        }
    }
  }

  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Info className="size-12 mb-4 opacity-50" />
        <p className="text-sm">Aucun log disponible</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filtres */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher dans les logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select value={levelFilter} onValueChange={setLevelFilter}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">Tous</SelectItem>
            <SelectItem value="INFO">INFO</SelectItem>
            <SelectItem value="WARNING">WARNING</SelectItem>
            <SelectItem value="ERROR">ERROR</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Liste des logs */}
      <ScrollArea className="h-[500px] pr-4">
        <Accordion type="single" collapsible className="space-y-2">
          {filteredLogs.map((log) => {
            const levelConfig = getLevelConfig(log.level)

            return (
              <AccordionItem key={log.id} value={log.id} className="border rounded-lg px-4">
                <AccordionTrigger className="hover:no-underline py-3">
                  <div className="flex items-center gap-2 w-full">
                    <Badge variant="outline" className={levelConfig.className}>
                      {levelConfig.icon}
                      <span className="ml-1">{log.level}</span>
                    </Badge>
                    <span className="text-sm font-medium">{log.step_name}</span>
                    <span className="text-xs text-muted-foreground ml-auto mr-2">
                      Step {log.step_order}
                    </span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="space-y-2 pb-3">
                  {/* Message */}
                  <div>
                    <div className="text-xs font-semibold text-muted-foreground mb-1">
                      Message
                    </div>
                    <p className="text-sm">{log.message}</p>
                  </div>

                  {/* Metadata */}
                  {log.metadata && (
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">
                        Métadonnées
                      </div>
                      <pre className="text-xs bg-muted/50 p-2 rounded-md overflow-x-auto max-h-[150px] border">
                        <code>{JSON.stringify(log.metadata, null, 2)}</code>
                      </pre>
                    </div>
                  )}

                  {/* Timestamp */}
                  <div className="text-xs text-muted-foreground">
                    {new Date(log.timestamp).toLocaleString('fr-FR')}
                  </div>
                </AccordionContent>
              </AccordionItem>
            )
          })}
        </Accordion>

        {filteredLogs.length === 0 && (
          <div className="text-center py-8 text-sm text-muted-foreground">
            Aucun log ne correspond aux filtres sélectionnés
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
