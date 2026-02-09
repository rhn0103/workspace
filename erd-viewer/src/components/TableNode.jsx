import { memo, useState, useCallback, useMemo } from 'react'
import { Handle, Position } from 'reactflow'
import { Eye, Pencil } from 'lucide-react'

const BORDER_BY_GROUP = {
  basic: 'border-emerald-500',
  financial: 'border-blue-500',
}

const HEADER_BG_BY_GROUP = {
  basic: 'bg-emerald-600',
  financial: 'bg-blue-600',
}

/** 엔티티 크기별: min-width, max-width, 컬럼 최대 개수, 컬럼 영역 max-height, 텍스트 크기 */
const ENTITY_SIZE_STYLES = {
  small: {
    wrapper: 'min-w-[140px] max-w-[200px]',
    columnArea: 'max-h-20 overflow-y-auto',
    columnLimit: 5,
    textSize: 'text-[11px]',
    typeSize: 'text-[9px]',
  },
  medium: {
    wrapper: 'min-w-[200px] max-w-[280px]',
    columnArea: 'max-h-40 overflow-y-auto',
    columnLimit: 12,
    textSize: 'text-xs',
    typeSize: 'text-[10px]',
  },
  large: {
    wrapper: 'min-w-[260px] max-w-[400px]',
    columnArea: 'max-h-72 overflow-y-auto',
    columnLimit: 999,
    textSize: 'text-sm',
    typeSize: 'text-xs',
  },
}

function TableNode({ data, selected }) {
  const [showPreview, setShowPreview] = useState(false)
  const group = data.group || 'basic'
  const borderClass = BORDER_BY_GROUP[group]
  const headerBg = HEADER_BG_BY_GROUP[group]
  const isEditMode = data.isEditMode === true
  const onEdit = data.onEditNode
  const entitySize = data.entitySize || 'medium'
  const sizeStyle = ENTITY_SIZE_STYLES[entitySize] || ENTITY_SIZE_STYLES.medium

  const { columnsToShow, restCount } = useMemo(() => {
    const cols = data.columns || []
    const limit = sizeStyle.columnLimit
    if (cols.length <= limit) return { columnsToShow: cols, restCount: 0 }
    return { columnsToShow: cols.slice(0, limit), restCount: cols.length - limit }
  }, [data.columns, sizeStyle.columnLimit])

  const handlePreviewEnter = useCallback(() => setShowPreview(true), [])
  const handlePreviewLeave = useCallback(() => setShowPreview(false), [])

  return (
    <div
      className={`
        rounded-lg overflow-hidden shadow-md
        border-2 ${borderClass} ${selected ? 'ring-2 ring-offset-2 ring-emerald-400' : ''}
        bg-white ${sizeStyle.wrapper}
      `}
    >
      <Handle id="target" type="target" position={Position.Left} className="!w-3 !h-3 !min-w-[12px] !min-h-[12px] !bg-gray-400 hover:!bg-emerald-500 !border-2 !border-white" isConnectable />
      <Handle id="source" type="source" position={Position.Right} className="!w-3 !h-3 !min-w-[12px] !min-h-[12px] !bg-gray-400 hover:!bg-emerald-500 !border-2 !border-white" isConnectable />

      {/* Header: 테이블 이름 + 보기/편집 아이콘 */}
      <div className={`${headerBg} px-3 py-2 flex items-center justify-between gap-1`}>
        <span className="font-semibold text-white text-sm truncate">{data.tableName}</span>
        <div className="flex items-center gap-0.5 shrink-0">
          {isEditMode && typeof onEdit === 'function' && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onEdit() }}
              className="p-1 rounded hover:bg-white/20 text-white/90 hover:text-white transition-colors"
              aria-label="테이블 편집"
              title="편집"
            >
              <Pencil className="w-4 h-4" />
            </button>
          )}
          <div
            className="relative"
            onMouseEnter={handlePreviewEnter}
            onMouseLeave={handlePreviewLeave}
          >
            <button
              type="button"
              className="p-1 rounded hover:bg-white/20 text-white/90 hover:text-white transition-colors"
              aria-label="샘플 데이터 미리보기"
            >
              <Eye className="w-4 h-4" />
            </button>
          {showPreview && (
            <div
              className="absolute left-full top-0 ml-2 z-50 min-w-[220px] max-w-[320px] rounded-lg shadow-xl border border-gray-200 bg-white p-2 text-left"
              onMouseEnter={handlePreviewEnter}
              onMouseLeave={handlePreviewLeave}
            >
              <div className="text-xs font-semibold text-gray-700 mb-2 border-b border-gray-200 pb-1">
                샘플 데이터 (3건)
              </div>
              <div className="text-xs text-gray-700 space-y-1 max-h-40 overflow-y-auto">
                {(data.sampleData || []).slice(0, 3).map((row, idx) => (
                  <div key={idx} className="bg-gray-50 rounded px-2 py-1 font-mono">
                    {Object.entries(row).map(([k, v]) => (
                      <div key={k} className="flex gap-2">
                        <span className="text-gray-500 shrink-0">{k}:</span>
                        <span className="truncate">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        </div>
      </div>

      {/* 컬럼 리스트 (크기에 따라 표시 개수·스크롤) */}
      <div className={`px-3 py-2 space-y-1 bg-gray-50/50 ${sizeStyle.columnArea}`}>
        {columnsToShow.map((col) => (
          <div
            key={col.name}
            className={`flex items-baseline justify-between gap-2 text-gray-700 ${sizeStyle.textSize}`}
          >
            <span className="font-mono truncate">
              {col.pk && <span className="text-amber-600 mr-1">PK</span>}
              {col.fk && <span className="text-cyan-600 mr-1">FK</span>}
              {col.name}
            </span>
            <span className={`text-gray-500 shrink-0 ${sizeStyle.typeSize}`}>{col.type}</span>
          </div>
        ))}
        {restCount > 0 && (
          <div className={`text-gray-500 pt-0.5 ${sizeStyle.typeSize}`}>
            외 {restCount}개 컬럼
          </div>
        )}
      </div>
    </div>
  )
}

export default memo(TableNode)
