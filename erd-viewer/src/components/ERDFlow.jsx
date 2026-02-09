import { useCallback, useMemo, useState } from 'react'
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  ReactFlowProvider,
} from 'reactflow'
import 'reactflow/dist/style.css'
import TableNode from './TableNode'
import { initialNodes as defaultNodes, initialEdges as defaultEdges } from '../data/erdData'

const nodeTypes = { tableNode: TableNode }

/** 호버된 노드와 연결된 노드/엣지 ID 집합 (BFS) */
function getConnectedIds(hoveredId, edges) {
  if (!hoveredId) return null
  const set = new Set([hoveredId])
  let changed = true
  while (changed) {
    changed = false
    edges.forEach((e) => {
      if (set.has(e.source) || set.has(e.target)) {
        if (!set.has(e.source)) { set.add(e.source); changed = true }
        if (!set.has(e.target)) { set.add(e.target); changed = true }
      }
    })
  }
  return set
}

function ERDFlowInner({
  nodes: controlledNodes,
  setNodes,
  edges: controlledEdges,
  setEdges,
  editMode = false,
  onEditNode,
  entitySize = 'medium',
  initialNodes = defaultNodes,
  initialEdges = defaultEdges,
}) {
  const [hoveredNodeId, setHoveredNodeId] = useState(null)

  const nodes = controlledNodes ?? initialNodes
  const edges = controlledEdges ?? initialEdges
  const setNodesSafe = setNodes ?? (() => {})
  const setEdgesSafe = setEdges ?? (() => {})

  const connectedIds = useMemo(
    () => getConnectedIds(hoveredNodeId, edges),
    [hoveredNodeId, edges]
  )

  const nodesWithMeta = useMemo(() => {
    return nodes.map((n) => ({
      ...n,
      connectable: editMode,
      data: {
        ...n.data,
        isEditMode: editMode,
        onEditNode: onEditNode ? () => onEditNode(n.id) : undefined,
        entitySize,
      },
    }))
  }, [nodes, editMode, onEditNode, entitySize])

  const nodesWithHover = useMemo(() => {
    if (!connectedIds) return nodesWithMeta
    return nodesWithMeta.map((n) => ({
      ...n,
      style: {
        ...n.style,
        opacity: connectedIds.has(n.id) ? 1 : 0.35,
        transition: 'opacity 0.2s ease',
      },
    }))
  }, [nodesWithMeta, connectedIds])

  const edgesWithHover = useMemo(() => {
    if (!connectedIds) return edges
    return edges.map((e) => ({
      ...e,
      style: {
        ...e.style,
        stroke: connectedIds.has(e.source) && connectedIds.has(e.target) ? '#3182CE' : '#9ca3af',
        opacity: connectedIds.has(e.source) && connectedIds.has(e.target) ? 1 : 0.3,
        strokeWidth: connectedIds.has(e.source) && connectedIds.has(e.target) ? 2.5 : 1.5,
        transition: 'opacity 0.2s ease, stroke 0.2s ease',
      },
    }))
  }, [edges, connectedIds])

  const onNodesChange = useCallback(
    (changes) => setNodesSafe((nds) => applyNodeChanges(changes, nds)),
    [setNodesSafe]
  )
  const onEdgesChange = useCallback(
    (changes) => setEdgesSafe((eds) => applyEdgeChanges(changes, eds)),
    [setEdgesSafe]
  )
  const onConnect = useCallback(
    (params) => {
      const label = params.sourceHandle && params.targetHandle
        ? `${params.sourceHandle} → ${params.targetHandle}`
        : `${params.source} → ${params.target}`
      const newEdge = {
        ...params,
        id: `e-${params.source}-${params.target}-${Date.now()}`,
        type: 'default',
        label,
        labelBgPadding: [4, 2],
        labelBgBorderRadius: 4,
        labelBgStyle: { fill: '#ffffff', fillOpacity: 0.95 },
        labelStyle: { fill: '#1f2937', fontSize: 10 },
      }
      setEdgesSafe((eds) => addEdge(newEdge, eds))
    },
    [setEdgesSafe]
  )
  const onNodeMouseEnter = useCallback((_, node) => setHoveredNodeId(node.id), [])
  const onNodeMouseLeave = useCallback(() => setHoveredNodeId(null), [])

  const isValidConnection = useCallback(() => true, [])

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodesWithHover}
        edges={edgesWithHover}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={editMode ? onConnect : undefined}
        onNodeMouseEnter={onNodeMouseEnter}
        onNodeMouseLeave={onNodeMouseLeave}
        onNodeDoubleClick={editMode && onEditNode ? (_, node) => onEditNode(node.id) : undefined}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        defaultEdgeOptions={{ type: 'default' }}
        className="bg-gray-100"
        nodesDraggable={editMode}
        nodesConnectable={editMode}
        elementsSelectable={true}
        deleteKeyCode={editMode ? 'Delete' : null}
        isValidConnection={editMode ? isValidConnection : undefined}
        connectionLineStyle={editMode ? { stroke: '#3182CE', strokeWidth: 2 } : undefined}
      >
        <Background color="#e5e7eb" gap={16} />
        <MiniMap
          nodeColor={(n) => (n.data?.group === 'financial' ? '#3b82f6' : '#10b981')}
          maskColor="rgba(249, 250, 251, 0.9)"
          className="!bg-white !border-gray-200"
        />
        <Controls
          className="!bg-white !border-gray-200 !rounded-lg [&>button]:!bg-gray-100 [&>button]:!text-gray-700 [&>button:hover]:!bg-gray-200"
          showInteractive={false}
        />
      </ReactFlow>
    </div>
  )
}

export default function ERDFlow(props) {
  return (
    <ReactFlowProvider>
      <ERDFlowInner {...props} />
    </ReactFlowProvider>
  )
}
