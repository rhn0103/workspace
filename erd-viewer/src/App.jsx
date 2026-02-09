import { useState, useCallback, useEffect } from 'react'
import ERDFlow from './components/ERDFlow'
import { loadEddData, saveEddData } from './data/erdStorage'
import { initialNodes, initialEdges } from './data/erdData'
import { Pencil, Plus, RotateCcw, Save, X } from 'lucide-react'

const ERD_API_URL = import.meta.env.VITE_ERD_API_URL || 'http://localhost:8765'

const DEFAULT_COLUMN = { name: '', type: 'varchar(100)', pk: false, fk: '' }
const DEFAULT_SAMPLE = [{ id: 1, sample: '샘플' }]

export default function App() {
  const [nodes, setNodes] = useState(() => loadEddData().nodes)
  const [edges, setEdges] = useState(() => loadEddData().edges)
  const [editMode, setEditMode] = useState(false)
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [addForm, setAddForm] = useState({
    id: '',
    tableName: '',
    group: 'basic',
    columns: [{ ...DEFAULT_COLUMN }],
  })
  const [syncStatus, setSyncStatus] = useState(null) // null | 'loading' | 'ok' | 'error'
  const [syncMessage, setSyncMessage] = useState('')
  const [entitySize, setEntitySize] = useState(() => {
    try {
      const v = localStorage.getItem('crm-erd-entity-size')
      if (v === 'small' || v === 'medium' || v === 'large') return v
    } catch {}
    return 'medium'
  })

  useEffect(() => {
    saveEddData(nodes, edges)
  }, [nodes, edges])

  const syncFromCrmApi = useCallback(() => {
    setSyncStatus('loading')
    setSyncMessage('')
    fetch(`${ERD_API_URL}/erd_tables.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`API ${res.status}`)
        return res.json()
      })
      .then((data) => {
        const tables = Array.isArray(data.tables) ? data.tables : []
        if (tables.length === 0) {
          setSyncStatus('ok')
          setSyncMessage('적재된 테이블이 없습니다. CRM에서 데이터를 먼저 업로드하세요.')
          return
        }
        setNodes((prev) => {
          const byTableName = new Map(prev.map((n) => [n.data?.tableName, n]))
          let maxX = Math.max(0, ...prev.map((n) => n.position?.x ?? 0))
          let maxY = Math.max(0, ...prev.map((n) => n.position?.y ?? 0))
          const next = [...prev]
          tables.forEach((t, i) => {
            const name = t.name
            const cols = (t.columns || []).map((c) => ({
              name: c.name,
              type: c.type || 'TEXT',
              pk: !!c.pk,
              fk: c.fk,
            }))
            const existing = byTableName.get(name)
            if (existing) {
              const idx = next.findIndex((n) => n.id === existing.id)
              if (idx >= 0 && cols.length > 0)
                next[idx] = { ...next[idx], data: { ...next[idx].data, columns: cols } }
            } else {
              const id = name
              if (next.some((n) => n.id === id)) return
              next.push({
                id,
                type: 'tableNode',
                position: { x: maxX + 100, y: maxY + 90 * i },
                data: {
                  tableName: name,
                  group: 'basic',
                  columns: cols.length ? cols : [{ name: 'id', type: 'INTEGER', pk: true }],
                  sampleData: [{ id: 1, sample: '적재 데이터' }],
                },
              })
              maxY += 90
            }
          })
          return next
        })
        setSyncStatus('ok')
        setSyncMessage(`${tables.length}개 테이블 반영 완료`)
      })
      .catch(() => {
        setSyncStatus('error')
        setSyncMessage('연결 실패. run.bat으로 실행했는지, ERD API(포트 8765)가 켜져 있는지 확인하세요.')
      })
  }, [])

  useEffect(() => {
    syncFromCrmApi()
  }, [syncFromCrmApi])

  const selectedNode = nodes.find((n) => n.id === selectedNodeId)

  const handleEditNode = useCallback((id) => setSelectedNodeId(id), [])
  const handleCloseEdit = useCallback(() => {
    setSelectedNodeId(null)
    setShowAddForm(false)
  }, [])

  const handleReset = useCallback(() => {
    if (window.confirm('기본 ERD로 초기화합니다. 편집 내용이 사라집니다.')) {
      setNodes(initialNodes)
      setEdges(initialEdges)
      handleCloseEdit()
    }
  }, [handleCloseEdit])

  const handleAddTable = useCallback(() => {
    const { id, tableName, group, columns } = addForm
    if (!id.trim() || !tableName.trim()) return
    const colList = columns.filter((c) => c.name.trim()).map((c) => ({
      name: c.name.trim(),
      type: c.type || 'varchar(100)',
      pk: !!c.pk,
      fk: c.fk?.trim() || undefined,
    }))
    if (colList.length === 0) colList.push({ name: 'id', type: 'bigint', pk: true })

    const lastNode = nodes[nodes.length - 1]
    const pos = lastNode?.position ? { x: lastNode.position.x + 80, y: lastNode.position.y + 80 } : { x: 100, y: 100 }

    setNodes((nds) => [
      ...nds,
      {
        id: id.trim(),
        type: 'tableNode',
        position: pos,
        data: {
          tableName: tableName.trim(),
          group: group || 'basic',
          columns: colList,
          sampleData: DEFAULT_SAMPLE,
        },
      },
    ])
    setAddForm({ id: '', tableName: '', group: 'basic', columns: [{ ...DEFAULT_COLUMN }] })
    setShowAddForm(false)
  }, [addForm, nodes])

  const handleSaveEdit = useCallback(
    (formData) => {
      if (!selectedNodeId) return
      setNodes((nds) =>
        nds.map((n) =>
          n.id === selectedNodeId
            ? { ...n, data: { ...n.data, ...formData } }
            : n
        )
      )
      setSelectedNodeId(null)
    },
    [selectedNodeId]
  )

  return (
    <div className="w-full h-full flex flex-col bg-gray-50">
      <header className="shrink-0 px-4 py-3 bg-white border-b border-gray-200 shadow-sm">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-lg font-semibold text-gray-800">CRM ERD 시각화</h1>
            <p className="text-sm text-gray-600 mt-0.5">
              {editMode
                ? '편집 모드: 노드 드래그, 연결선 그리기, Delete 키로 삭제, 연필 아이콘으로 테이블 편집'
                : '테이블에 마우스를 올리면 연결된 노드가 하이라이트됩니다. 보기 아이콘으로 샘플 데이터를 확인할 수 있습니다.'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={entitySize}
              onChange={(e) => {
                const v = e.target.value
                setEntitySize(v)
                try { localStorage.setItem('crm-erd-entity-size', v) } catch {}
              }}
              className="px-2 py-1.5 rounded-lg border border-gray-300 bg-white text-gray-700 text-sm"
              title="엔티티(테이블) 박스 크기"
            >
              <option value="small">엔티티: 작게</option>
              <option value="medium">엔티티: 보통</option>
              <option value="large">엔티티: 크게</option>
            </select>
            <button
              type="button"
              onClick={syncFromCrmApi}
              disabled={syncStatus === 'loading'}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm"
              title="CRM에 적재된 테이블을 ERD에 반영"
            >
              {syncStatus === 'loading' ? '반영 중...' : 'CRM 데이터 반영'}
            </button>
            {syncMessage && (
              <span className={`text-sm ${syncStatus === 'error' ? 'text-red-600' : 'text-gray-600'}`}>
                {syncMessage}
              </span>
            )}
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={editMode}
                onChange={(e) => setEditMode(e.target.checked)}
                className="rounded"
              />
              <Pencil className="w-4 h-4" />
              편집 모드
            </label>
            {editMode && (
              <>
                <button
                  type="button"
                  onClick={() => setShowAddForm(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm"
                >
                  <Plus className="w-4 h-4" />
                  테이블 추가
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-800 text-sm"
                >
                  <RotateCcw className="w-4 h-4" />
                  초기화
                </button>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1 min-h-0 relative">
        <ERDFlow
          nodes={nodes}
          setNodes={setNodes}
          edges={edges}
          setEdges={setEdges}
          editMode={editMode}
          onEditNode={handleEditNode}
          entitySize={entitySize}
        />

        {/* 테이블 추가 폼 */}
        {showAddForm && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
            <div className="bg-white rounded-xl border border-gray-200 shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-800">테이블 추가</h2>
                <button type="button" onClick={handleCloseEdit} className="p-1 rounded hover:bg-gray-100 text-gray-500">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-4 space-y-3">
                <div>
                  <label className="block text-xs text-gray-600 mb-1">테이블 ID (영문)</label>
                  <input
                    type="text"
                    value={addForm.id}
                    onChange={(e) => setAddForm((f) => ({ ...f, id: e.target.value }))}
                    placeholder="예: payment"
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 text-gray-800 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-600 mb-1">테이블 이름</label>
                  <input
                    type="text"
                    value={addForm.tableName}
                    onChange={(e) => setAddForm((f) => ({ ...f, tableName: e.target.value }))}
                    placeholder="예: 결제"
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 text-gray-800 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-600 mb-1">그룹</label>
                  <select
                    value={addForm.group}
                    onChange={(e) => setAddForm((f) => ({ ...f, group: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 text-gray-800 text-sm"
                  >
                    <option value="basic">기본 (초록)</option>
                    <option value="financial">금융 (파랑)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-600 mb-1">컬럼 (이름, 타입, PK, FK)</label>
                  {addForm.columns.map((col, i) => (
                    <div key={i} className="flex gap-2 mb-2">
                      <input
                        type="text"
                        value={col.name}
                        onChange={(e) =>
                          setAddForm((f) => ({
                            ...f,
                            columns: f.columns.map((c, j) => (j === i ? { ...c, name: e.target.value } : c)),
                          }))
                        }
                        placeholder="컬럼명"
                        className="flex-1 px-2 py-1.5 rounded bg-gray-50 border border-gray-200 text-gray-800 text-xs"
                      />
                      <input
                        type="text"
                        value={col.type}
                        onChange={(e) =>
                          setAddForm((f) => ({
                            ...f,
                            columns: f.columns.map((c, j) => (j === i ? { ...c, type: e.target.value } : c)),
                          }))
                        }
                        placeholder="타입"
                        className="w-24 px-2 py-1.5 rounded bg-gray-50 border border-gray-200 text-gray-800 text-xs"
                      />
                      <label className="flex items-center gap-1 text-xs text-gray-600 shrink-0">
                        <input
                          type="checkbox"
                          checked={col.pk}
                          onChange={(e) =>
                            setAddForm((f) => ({
                              ...f,
                              columns: f.columns.map((c, j) => (j === i ? { ...c, pk: e.target.checked } : c)),
                            }))
                          }
                        />
                        PK
                      </label>
                      <button
                        type="button"
                        onClick={() =>
                          setAddForm((f) => ({ ...f, columns: f.columns.filter((_, j) => j !== i) }))
                        }
                        className="text-gray-500 hover:text-red-500 text-xs"
                      >
                        삭제
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => setAddForm((f) => ({ ...f, columns: [...f.columns, { ...DEFAULT_COLUMN }] }))}
                    className="text-xs text-emerald-400 hover:text-emerald-300"
                  >
                    + 컬럼 추가
                  </button>
                </div>
              </div>
              <div className="flex justify-end gap-2 p-4 border-t border-gray-200">
                <button type="button" onClick={handleCloseEdit} className="px-3 py-1.5 rounded-lg bg-gray-200 text-gray-800 text-sm">
                  취소
                </button>
                <button type="button" onClick={handleAddTable} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-sm">
                  <Plus className="w-4 h-4" /> 추가
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 테이블 편집 폼 */}
        {selectedNode && !showAddForm && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
            <EditTableForm
              node={selectedNode}
              onSave={handleSaveEdit}
              onClose={handleCloseEdit}
            />
          </div>
        )}
      </main>
    </div>
  )
}

function EditTableForm({ node, onSave, onClose }) {
  const [tableName, setTableName] = useState(node.data?.tableName ?? '')
  const [group, setGroup] = useState(node.data?.group ?? 'basic')
  const [columns, setColumns] = useState(
    (node.data?.columns ?? []).length ? node.data.columns : [{ ...DEFAULT_COLUMN }]
  )

  const handleSave = () => {
    const colList = columns.filter((c) => c.name.trim()).map((c) => ({
      name: c.name.trim(),
      type: c.type || 'varchar(100)',
      pk: !!c.pk,
      fk: c.fk?.trim() || undefined,
    }))
    onSave({ tableName: tableName.trim(), group, columns: colList.length ? colList : [{ name: 'id', type: 'bigint', pk: true }] })
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-800">테이블 편집 · {node.id}</h2>
        <button type="button" onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-500">
          <X className="w-5 h-5" />
        </button>
      </div>
      <div className="p-4 space-y-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">테이블 이름</label>
          <input
            type="text"
            value={tableName}
            onChange={(e) => setTableName(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 text-gray-800 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">그룹</label>
          <select
            value={group}
            onChange={(e) => setGroup(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 text-gray-800 text-sm"
          >
            <option value="basic">기본 (초록)</option>
            <option value="financial">금융 (파랑)</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">컬럼</label>
          {columns.map((col, i) => (
            <div key={i} className="flex gap-2 mb-2">
              <input
                type="text"
                value={col.name}
                onChange={(e) => setColumns((c) => c.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))}
                placeholder="컬럼명"
                className="flex-1 px-2 py-1.5 rounded bg-gray-50 border border-gray-200 text-gray-800 text-xs"
              />
              <input
                type="text"
                value={col.type}
                onChange={(e) => setColumns((c) => c.map((x, j) => (j === i ? { ...x, type: e.target.value } : x)))}
                placeholder="타입"
                className="w-24 px-2 py-1.5 rounded bg-gray-50 border border-gray-200 text-gray-800 text-xs"
              />
              <label className="flex items-center gap-1 text-xs text-gray-600 shrink-0">
                <input
                  type="checkbox"
                  checked={col.pk}
                  onChange={(e) => setColumns((c) => c.map((x, j) => (j === i ? { ...x, pk: e.target.checked } : x)))}
                />
                PK
              </label>
              <button
                type="button"
                onClick={() => setColumns((c) => c.filter((_, j) => j !== i))}
                className="text-gray-500 hover:text-red-500 text-xs"
              >
                삭제
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => setColumns((c) => [...c, { ...DEFAULT_COLUMN }])}
            className="text-xs text-emerald-600 hover:text-emerald-500"
          >
            + 컬럼 추가
          </button>
        </div>
      </div>
      <div className="flex justify-end gap-2 p-4 border-t border-gray-200">
        <button type="button" onClick={onClose} className="px-3 py-1.5 rounded-lg bg-gray-200 text-gray-800 text-sm">
          취소
        </button>
        <button type="button" onClick={handleSave} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-sm">
          <Save className="w-4 h-4" /> 저장
        </button>
      </div>
    </div>
  )
}
