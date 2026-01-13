"use client"

import { useMemo } from 'react'
import { ReactFlow, Background, Controls, MiniMap, Node, Edge } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import type { WorkflowStep } from '@/services/automations/automations.types'
import { cn } from '@/lib/utils'
import { Activity, GitBranch, Repeat, Clock } from 'lucide-react'

// Custom node components
const ActionNode = ({ data }: { data: any }) => (
  <div className={cn(
    "px-4 py-3 rounded-lg bg-white dark:bg-gray-800 border-2 shadow-sm min-w-[180px]",
    data.enabled ? "border-blue-500" : "border-gray-300 opacity-60"
  )}>
    <div className="flex items-center gap-2 mb-1">
      <Activity className="size-4 text-blue-500" />
      <div className="font-semibold text-sm truncate">{data.label}</div>
    </div>
    <div className="text-xs text-muted-foreground">{data.step_subtype}</div>
    {data.step_order !== undefined && (
      <div className="text-xs text-muted-foreground mt-1">Step {data.step_order}</div>
    )}
  </div>
)

const ConditionNode = ({ data }: { data: any }) => (
  <div className={cn(
    "px-4 py-3 rounded-lg bg-white dark:bg-gray-800 border-2 shadow-sm min-w-[180px]",
    data.enabled ? "border-green-500" : "border-gray-300 opacity-60"
  )}>
    <div className="flex items-center gap-2 mb-1">
      <GitBranch className="size-4 text-green-500" />
      <div className="font-semibold text-sm truncate">{data.label}</div>
    </div>
    <div className="text-xs text-muted-foreground">if/else</div>
    {data.step_order !== undefined && (
      <div className="text-xs text-muted-foreground mt-1">Step {data.step_order}</div>
    )}
  </div>
)

const LoopNode = ({ data }: { data: any }) => (
  <div className={cn(
    "px-4 py-3 rounded-lg bg-white dark:bg-gray-800 border-2 shadow-sm min-w-[180px]",
    data.enabled ? "border-purple-500" : "border-gray-300 opacity-60"
  )}>
    <div className="flex items-center gap-2 mb-1">
      <Repeat className="size-4 text-purple-500" />
      <div className="font-semibold text-sm truncate">{data.label}</div>
    </div>
    <div className="text-xs text-muted-foreground">loop</div>
    {data.step_order !== undefined && (
      <div className="text-xs text-muted-foreground mt-1">Step {data.step_order}</div>
    )}
  </div>
)

const DelayNode = ({ data }: { data: any }) => (
  <div className={cn(
    "px-4 py-3 rounded-lg bg-white dark:bg-gray-800 border-2 shadow-sm min-w-[180px]",
    data.enabled ? "border-orange-500" : "border-gray-300 opacity-60"
  )}>
    <div className="flex items-center gap-2 mb-1">
      <Clock className="size-4 text-orange-500" />
      <div className="font-semibold text-sm truncate">{data.label}</div>
    </div>
    <div className="text-xs text-muted-foreground">delay</div>
    {data.step_order !== undefined && (
      <div className="text-xs text-muted-foreground mt-1">Step {data.step_order}</div>
    )}
  </div>
)

const nodeTypes = {
  action: ActionNode,
  condition: ConditionNode,
  loop: LoopNode,
  delay: DelayNode,
}

function getNodeType(step: WorkflowStep): string {
  if (step.step_type === 'action') {
    return 'action'
  }
  if (step.step_type === 'control') {
    if (step.step_subtype === 'condition') return 'condition'
    if (step.step_subtype === 'loop') return 'loop'
    if (step.step_subtype === 'delay') return 'delay'
  }
  return 'action' // default
}

function transformStepsToFlow(steps: WorkflowStep[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = []
  const edges: Edge[] = []

  // 1. Créer les nodes
  steps.forEach((step) => {
    nodes.push({
      id: step.id,
      type: getNodeType(step),
      position: { x: 0, y: 0 }, // Sera calculé par dagre
      data: {
        label: step.step_name,
        step_order: step.step_order,
        step_type: step.step_type,
        step_subtype: step.step_subtype,
        enabled: step.enabled,
        config: step.config,
      },
    })
  })

  // 2. Créer les edges
  steps.forEach((step, index) => {
    const currentNode = nodes.find((n) => n.data.step_order === step.step_order)!

    // Edge par défaut: step N → step N+1
    if (index < steps.length - 1) {
      const nextNode = nodes.find((n) => n.data.step_order === step.step_order + 1)!
      edges.push({
        id: `${currentNode.id}-${nextNode.id}`,
        source: currentNode.id,
        target: nextNode.id,
        type: 'smoothstep',
        animated: false,
      })
    }

    // Edge spécial pour condition (jump)
    if (step.step_type === 'control' && step.step_subtype === 'condition') {
      const targetStepOrder = step.config?.target_step
      if (targetStepOrder !== undefined) {
        const targetNode = nodes.find((n) => n.data.step_order === targetStepOrder)
        if (targetNode) {
          edges.push({
            id: `${currentNode.id}-${targetNode.id}-jump`,
            source: currentNode.id,
            target: targetNode.id,
            type: 'smoothstep',
            animated: true,
            label: 'if true',
            style: { stroke: '#10b981', strokeWidth: 2 },
            labelBgStyle: { fill: '#10b981', opacity: 0.2 },
          })
        }
      }
    }

    // Edges pour loop
    if (step.step_type === 'control' && step.step_subtype === 'loop') {
      const loopSteps = step.config?.loop_steps || []
      if (loopSteps.length > 0) {
        // Edge vers le premier step de la boucle
        const firstLoopNode = nodes.find((n) => n.data.step_order === loopSteps[0])
        if (firstLoopNode) {
          edges.push({
            id: `${currentNode.id}-${firstLoopNode.id}-loop-start`,
            source: currentNode.id,
            target: firstLoopNode.id,
            type: 'smoothstep',
            animated: true,
            label: 'for each',
            style: { stroke: '#8b5cf6', strokeWidth: 2 },
            labelBgStyle: { fill: '#8b5cf6', opacity: 0.2 },
          })

          // Edge de retour: dernier step boucle → loop node
          const lastLoopNode = nodes.find(
            (n) => n.data.step_order === loopSteps[loopSteps.length - 1]
          )
          if (lastLoopNode) {
            edges.push({
              id: `${lastLoopNode.id}-${currentNode.id}-loop-back`,
              source: lastLoopNode.id,
              target: currentNode.id,
              type: 'smoothstep',
              animated: true,
              style: { stroke: '#8b5cf6', strokeWidth: 2, strokeDasharray: '5 5' },
            })
          }
        }
      }
    }
  })

  return { nodes, edges }
}

function applyDagreLayout(nodes: Node[], edges: Edge[]): Node[] {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 100 })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 200, height: 80 })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  return nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - 100, // centrer
        y: nodeWithPosition.y - 40,
      },
    }
  })
}

interface WorkflowVisualizationProps {
  steps: WorkflowStep[]
}

export function WorkflowVisualization({ steps }: WorkflowVisualizationProps) {
  const { nodes, edges } = useMemo(() => {
    if (!steps || steps.length === 0) {
      return { nodes: [], edges: [] }
    }

    const { nodes: rawNodes, edges: rawEdges } = transformStepsToFlow(steps)
    const layoutedNodes = applyDagreLayout(rawNodes, rawEdges)
    return { nodes: layoutedNodes, edges: rawEdges }
  }, [steps])

  if (!steps || steps.length === 0) {
    return (
      <div className="w-full h-[500px] border rounded-lg flex items-center justify-center bg-muted/20">
        <p className="text-muted-foreground">Aucune étape configurée</p>
      </div>
    )
  }

  return (
    <div className="w-full h-[600px] border rounded-lg bg-muted/5">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        // Lecture seule
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        panOnDrag={true}
        zoomOnScroll={true}
        zoomOnPinch={true}
        zoomOnDoubleClick={false}
        minZoom={0.5}
        maxZoom={1.5}
      >
        <Background />
        <Controls showInteractive={false} />
        <MiniMap
          nodeStrokeWidth={3}
          zoomable
          pannable
        />
      </ReactFlow>
    </div>
  )
}
