import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'
import AuthPage from './components/AuthPage.jsx'
import Chatbot from './components/Chatbot.jsx'
import { getCurrentToken, signOut, getUserEmail } from './auth/cognito.js'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

/* ────────────────────────────────────────────────────────────
   CONFIG
──────────────────────────────────────────────────────────── */
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

const CATEGORIES = [
  'Food', 'Transport', 'Shopping', 'Utilities',
  'Entertainment', 'Health', 'Subscriptions', 'Income', 'Transfer', 'Other',
]

const CATEGORY_VI = {
  Food: 'Ăn uống', Transport: 'Di chuyển', Shopping: 'Mua sắm',
  Utilities: 'Tiện ích', Entertainment: 'Giải trí', Health: 'Sức khỏe',
  Subscriptions: 'Đăng ký', Income: 'Thu nhập', Transfer: 'Chuyển khoản', Other: 'Khác',
}

const CATEGORY_ICON = {
  Food: '🍜', Transport: '🚗', Shopping: '🛍️', Utilities: '💡',
  Entertainment: '🎬', Health: '💊', Subscriptions: '📱', Income: '💰',
  Transfer: '🔄', Other: '📌',
}

const CATEGORY_COLOR = {
  Food: '#f97316', Transport: '#06b6d4', Shopping: '#ec4899',
  Utilities: '#8b5cf6', Entertainment: '#f59e0b', Health: '#10b981',
  Subscriptions: '#6366f1', Income: '#22d3ee', Transfer: '#94a3b8', Other: '#64748b',
}

const CONFIDENCE_VI = {
  high: 'Cao', medium: 'TB', low: 'Thấp', 'low-fallback': 'Dự phòng',
}

/* ────────────────────────────────────────────────────────────
   HELPERS
──────────────────────────────────────────────────────────── */
const fmtVND = (num) => {
  const abs = Math.abs(num)
  if (abs >= 1_000_000) return (num / 1_000_000).toFixed(1) + ' tr'
  if (abs >= 1_000) return (num / 1_000).toFixed(0) + 'k'
  return num.toLocaleString('vi-VN')
}

const fmtFull = (num) =>
  new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(num)

/* ────────────────────────────────────────────────────────────
   DONUT CHART
──────────────────────────────────────────────────────────── */
function DonutChart({ data, total }) {
  const [hovered, setHovered] = useState(null)
  const SIZE = 180
  const CX = SIZE / 2
  const CY = SIZE / 2
  const R_OUTER = 78
  const R_INNER = 52
  const GAP = 2

  if (!data || data.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-icon">📊</span>
        <span className="empty-text">Chưa có dữ liệu để hiển thị biểu đồ</span>
      </div>
    )
  }

  // Only expenses (negative amounts)
  const expenses = data.filter(d => d.total < 0)
  const totalExp = expenses.reduce((s, d) => s + Math.abs(d.total), 0)
  if (totalExp === 0) return null

  let currentAngle = -Math.PI / 2
  const slices = expenses.map((d) => {
    const fraction = Math.abs(d.total) / totalExp
    const angle = fraction * 2 * Math.PI - (GAP * Math.PI) / 180
    const startAngle = currentAngle + (GAP * Math.PI) / 360
    const endAngle = currentAngle + angle + (GAP * Math.PI) / 360
    currentAngle += fraction * 2 * Math.PI

    const x1 = CX + R_OUTER * Math.cos(startAngle)
    const y1 = CY + R_OUTER * Math.sin(startAngle)
    const x2 = CX + R_OUTER * Math.cos(endAngle)
    const y2 = CY + R_OUTER * Math.sin(endAngle)
    const x3 = CX + R_INNER * Math.cos(endAngle)
    const y3 = CY + R_INNER * Math.sin(endAngle)
    const x4 = CX + R_INNER * Math.cos(startAngle)
    const y4 = CY + R_INNER * Math.sin(startAngle)
    const largeArc = angle > Math.PI ? 1 : 0

    return {
      ...d,
      path: `M ${x1} ${y1} A ${R_OUTER} ${R_OUTER} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${R_INNER} ${R_INNER} 0 ${largeArc} 0 ${x4} ${y4} Z`,
      pct: (fraction * 100).toFixed(1),
      color: CATEGORY_COLOR[d.category] || '#64748b',
    }
  })

  const hoveredSlice = hovered !== null ? slices.find(s => s.category === hovered) : null

  return (
    <div className="donut-chart-wrapper">
      <div className="donut-svg-container">
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width={SIZE} height={SIZE}>
          {slices.map((s) => (
            <path
              key={s.category}
              d={s.path}
              fill={s.color}
              opacity={hovered && hovered !== s.category ? 0.3 : 1}
              style={{ transition: 'opacity 0.2s, transform 0.2s', transformOrigin: `${CX}px ${CY}px` }}
              transform={hovered === s.category ? 'scale(1.04)' : 'scale(1)'}
              onMouseEnter={() => setHovered(s.category)}
              onMouseLeave={() => setHovered(null)}
            />
          ))}
        </svg>
        <div className="donut-center-text">
          {hoveredSlice ? (
            <>
              <span className="donut-center-label">{CATEGORY_VI[hoveredSlice.category]}</span>
              <span className="donut-center-value" style={{ color: hoveredSlice.color, fontSize: '0.95rem' }}>
                {fmtVND(Math.abs(hoveredSlice.total))}
              </span>
            </>
          ) : (
            <>
              <span className="donut-center-label">Tổng chi</span>
              <span className="donut-center-value">{fmtVND(Math.abs(totalExp))}</span>
            </>
          )}
        </div>
      </div>

      <div className="donut-legend">
        {slices.sort((a, b) => Math.abs(b.total) - Math.abs(a.total)).map((s) => (
          <div
            key={s.category}
            className="legend-item"
            onMouseEnter={() => setHovered(s.category)}
            onMouseLeave={() => setHovered(null)}
            style={{ opacity: hovered && hovered !== s.category ? 0.4 : 1, transition: 'opacity 0.2s' }}
          >
            <span className="legend-dot" style={{ background: s.color }} />
            <span className="legend-name">
              {CATEGORY_ICON[s.category]} {CATEGORY_VI[s.category]}
            </span>
            <span className="legend-amount">{fmtVND(Math.abs(s.total))}</span>
            <span className="legend-pct">{s.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ────────────────────────────────────────────────────────────
   CATEGORY EDIT MODAL
──────────────────────────────────────────────────────────── */
function EditModal({ txn, onClose, onSave }) {
  const [selected, setSelected] = useState(txn.category)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    await onSave(txn.id, selected)
    setSaving(false)
    onClose()
  }

  return (
    <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <h3 className="modal-title">✏️ Sửa danh mục</h3>
        <p className="modal-sub" title={txn.description}>{txn.description}</p>
        <select
          id="cat-select"
          className="modal-select filter-select"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          {CATEGORIES.map(c => (
            <option key={c} value={c}>{CATEGORY_ICON[c]} {CATEGORY_VI[c]}</option>
          ))}
        </select>
        <div className="modal-actions">
          <button className="btn btn-ghost btn-sm" onClick={onClose} disabled={saving}>Huỷ</button>
          <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
            {saving ? <><span className="spinner" />Đang lưu...</> : '💾 Lưu'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ────────────────────────────────────────────────────────────
   BUDGET SETUP MODAL
──────────────────────────────────────────────────────────── */
function BudgetSetupModal({ budgets, onClose, onSave }) {
  const [cat, setCat] = useState('Food')
  const [amt, setAmt] = useState(budgets?.Food || 0)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    await onSave(cat, Number(amt))
    setSaving(false)
    onClose()
  }

  return (
    <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <h3 className="modal-title">⚙️ Cài đặt ngân sách</h3>
        <div style={{marginBottom: 10}}>
          <label>Danh mục</label>
          <select className="modal-select filter-select" value={cat} onChange={e => {setCat(e.target.value); setAmt(budgets?.[e.target.value] || 0)}}>
            {CATEGORIES.map(c => <option key={c} value={c}>{CATEGORY_ICON[c]} {CATEGORY_VI[c]}</option>)}
          </select>
        </div>
        <div style={{marginBottom: 20}}>
          <label>Giới hạn (VNĐ)</label>
          <input type="number" className="modal-input" value={amt} onChange={e => setAmt(e.target.value)} />
        </div>
        <div className="modal-actions">
          <button className="btn btn-ghost btn-sm" onClick={onClose} disabled={saving}>Huỷ</button>
          <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>💾 Lưu</button>
        </div>
      </div>
    </div>
  )
}

/* ────────────────────────────────────────────────────────────
   ADD TRANSACTION MODAL
──────────────────────────────────────────────────────────── */
function AddTransactionModal({ onClose, onSave }) {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [desc, setDesc] = useState('')
  const [amt, setAmt] = useState('')
  const [cat, setCat] = useState('Food')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    await onSave({ date, description: desc, amount: Number(amt), category: cat })
    setSaving(false)
    onClose()
  }

  return (
    <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <h3 className="modal-title">➕ Giao dịch thủ công</h3>
        <div style={{display: 'flex', gap: 10, marginBottom: 10}}>
          <div style={{flex: 1}}>
            <label>Ngày</label>
            <input type="date" className="modal-input" value={date} onChange={e => setDate(e.target.value)} />
          </div>
          <div style={{flex: 1}}>
            <label>Số tiền</label>
            <input type="number" className="modal-input" placeholder="-100000 hoặc 50000" value={amt} onChange={e => setAmt(e.target.value)} />
          </div>
        </div>
        <div style={{marginBottom: 10}}>
          <label>Mô tả</label>
          <input type="text" className="modal-input" placeholder="Ăn trưa..." value={desc} onChange={e => setDesc(e.target.value)} />
        </div>
        <div style={{marginBottom: 20}}>
          <label>Danh mục</label>
          <select className="modal-select filter-select" value={cat} onChange={e => setCat(e.target.value)}>
            {CATEGORIES.map(c => <option key={c} value={c}>{CATEGORY_ICON[c]} {CATEGORY_VI[c]}</option>)}
          </select>
        </div>
        <div className="modal-actions">
          <button className="btn btn-ghost btn-sm" onClick={onClose} disabled={saving}>Huỷ</button>
          <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>💾 Thêm</button>
        </div>
      </div>
    </div>
  )
}

/* ────────────────────────────────────────────────────────────
   CSV PREVIEW MODAL
──────────────────────────────────────────────────────────── */
function CSVPreviewModal({ previewData, onClose, onConfirm }) {
  const [colDate, setColDate] = useState('0')
  const [colDesc, setColDesc] = useState('1')
  const [colAmt, setColAmt] = useState('2')

  return (
    <div className="modal-backdrop" style={{zIndex: 999}} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{maxWidth: 600}}>
        <h3 className="modal-title">Cấu hình Cột CSV</h3>
        <p className="modal-sub">Vui lòng ánh xạ cột dữ liệu để AI phân tích chính xác</p>
        <div style={{display: 'flex', gap: 10, marginBottom: 10}}>
          <div style={{flex: 1}}><label>Cột Ngày</label><input type="number" className="modal-input" value={colDate} onChange={e=>setColDate(e.target.value)} /></div>
          <div style={{flex: 1}}><label>Cột Mô tả</label><input type="number" className="modal-input" value={colDesc} onChange={e=>setColDesc(e.target.value)} /></div>
          <div style={{flex: 1}}><label>Cột Số tiền</label><input type="number" className="modal-input" value={colAmt} onChange={e=>setColAmt(e.target.value)} /></div>
        </div>
        <div style={{maxHeight: 200, overflow: 'auto', marginBottom: 20, fontSize: 12, background: '#f8fafc', padding: 8, borderRadius: 8}}>
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <tbody>
              {previewData.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => <td key={j} style={{border: '1px solid #e2e8f0', padding: 4}}>[{j}] {cell}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="modal-actions">
          <button className="btn btn-ghost btn-sm" onClick={onClose}>Huỷ</button>
          <button className="btn btn-primary btn-sm" onClick={() => onConfirm({date: colDate, description: colDesc, amount: colAmt})}>🚀 Tiếp tục Tải lên</button>
        </div>
      </div>
    </div>
  )
}

/* ────────────────────────────────────────────────────────────
   MAIN APP
──────────────────────────────────────────────────────────── */
export default function App() {
  /* ── AUTH STATE ── */
  const [token, setToken]           = useState(null)   // JWT token
  const [userEmail, setUserEmail]   = useState('')
  const [authChecked, setAuthChecked] = useState(false) // prevent flicker

  // Khôi phục session khi reload trang
  useEffect(() => {
    getCurrentToken().then(async (t) => {
      if (t) {
        setToken(t)
        const email = await getUserEmail()
        setUserEmail(email)
      }
      setAuthChecked(true)
    })
  }, [])

  const handleAuthenticated = (newToken, email) => {
    setToken(newToken)
    setUserEmail(email)
  }

  const [summary, setSummary]       = useState(null)
  const [transactions, setTxns]     = useState([])
  const [month, setMonth]           = useState('')
  const [loading, setLoading]       = useState(false)
  const [uploading, setUploading]   = useState(false)
  const [dragOver, setDragOver]     = useState(false)
  const [alert, setAlert]           = useState(null)  // { type, msg }
  const [editTxn, setEditTxn]       = useState(null)
  const [clearing, setClearing]     = useState(false)
  const [budgetAlerts, setBudgetAlerts] = useState([])
  const [showBudget, setShowBudget] = useState(false)
  const [showAddTxn, setShowAddTxn] = useState(false)
  const [csvPreviewData, setCsvPreviewData] = useState(null)
  const [pendingFile, setPendingFile] = useState(null)
  const fileRef                     = useRef()

  const handleSignOut = () => {
    signOut()
    setToken(null)
    setUserEmail('')
    setSummary(null)
    setTxns([])
  }

  /* ── authFetch: tự động đính token vào mọi API call ── */
  const authFetch = useCallback((url, options = {}) => {
    const headers = {
      ...(options.headers || {}),
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    }
    return fetch(url, { ...options, headers })
  }, [token])

  /* --- Fetch data --- */
  const fetchData = useCallback(async (m) => {
    setLoading(true)
    try {
      const q = m ? `?month=${m}` : ''
      const [sumRes, txnRes, budRes] = await Promise.all([
        authFetch(`${API_BASE}/summary${q}`),
        authFetch(`${API_BASE}/transactions${q}`),
        authFetch(`${API_BASE}/budgets`),
      ])
      if (!sumRes.ok || !txnRes.ok) throw new Error('Không thể tải dữ liệu từ server')
      const sumData = await sumRes.json()
      const txnData = await txnRes.json()
      const budData = budRes.ok ? await budRes.json() : { alerts: [] }
      setSummary(sumData)
      setTxns(txnData.transactions || [])
      setBudgetAlerts(budData.alerts || [])
    } catch (e) {
      setAlert({ type: 'error', msg: e.message || 'Lỗi kết nối đến server' })
    } finally {
      setLoading(false)
    }
  }, [authFetch])

  useEffect(() => { if (token) fetchData(month) }, [month, fetchData, token])

  /* --- Poll job status --- */
  const pollJobStatus = useCallback(async (job_id) => {
    const MAX_WAIT = 600  // tối đa 10 phút
    const INTERVAL = 2000 // poll mỗi 2 giây
    let elapsed = 0
    while (elapsed < MAX_WAIT * 1000) {
      await new Promise(r => setTimeout(r, INTERVAL))
      elapsed += INTERVAL
      const res = await authFetch(`${API_BASE}/job-status/${job_id}`)
      const job = await res.json()
      if (job.status === 'COMPLETED') {
        return { rows_inserted: job.rows_inserted, filename: job_id, sample_categorized: [] }
      }
      if (job.status === 'FAILED') {
        throw new Error(`Xử lý thất bại: ${job.error || 'Lỗi không xác định'}`)
      }
      // QUEUED hoặc PROCESSING → tiếp tục poll
    }
    throw new Error('Xử lý quá thời gian chờ (10 phút)')
  }, [authFetch])

  const handleUploadClick = (file) => {
    if (!file) return
    const ext = file.name.toLowerCase().split('.').pop()
    if (!['csv', 'pdf'].includes(ext)) {
      setAlert({ type: 'error', msg: 'Chỉ hỗ trợ file CSV hoặc PDF!' })
      return
    }
    
    if (ext === 'csv') {
      const reader = new FileReader()
      reader.onload = (e) => {
        const text = e.target.result
        const rows = text.split('\n').map(r => r.split(',')).slice(0, 5)
        setCsvPreviewData(rows)
        setPendingFile(file)
      }
      reader.readAsText(file)
    } else {
      handleUpload(file, null)
    }
  }

  /* --- Upload --- */
  const handleUpload = async (file, mapping) => {
    setUploading(true)
    setAlert(null)

    try {
      // Bước 1: Xin presigned URL từ backend
      const reqRes = await authFetch(`${API_BASE}/upload-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name }),
      })
      if (!reqRes.ok) {
        const err = await reqRes.json().catch(() => ({}))
        throw new Error(err.detail || 'Không thể tạo upload request')
      }
      const { upload_url, s3_key, fallback_to_multipart } = await reqRes.json()

      let data

      if (fallback_to_multipart || !upload_url) {
        // Fallback: local dev — file vẫn đi qua /upload như cũ
        const form = new FormData()
        form.append('file', file)
        const res = await authFetch(`${API_BASE}/upload`, { method: 'POST', body: form })
        data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Upload thất bại')
      } else {
        // Bước 2: PUT file trực tiếp lên S3 (không qua Lambda)
        const putRes = await fetch(upload_url, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/octet-stream' },
          body: file,
        })
        if (!putRes.ok) throw new Error(`Upload lên S3 thất bại (HTTP ${putRes.status})`)

        // Bước 3: Enqueue job vào SQS — trả về job_id ngay, không chờ xử lý
        const enqueueRes = await authFetch(`${API_BASE}/enqueue`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ s3_key, filename: file.name, mapping }),
        })
        const enqueueData = await enqueueRes.json()
        if (!enqueueRes.ok) throw new Error(enqueueData.detail || 'Enqueue thất bại')

        const { job_id } = enqueueData
        setAlert({ type: 'warning', msg: `⏳ Đang xử lý file... (job: ${job_id.slice(0, 8)})` })

        // Bước 4: Polling job status mỗi 2 giây
        data = await pollJobStatus(job_id)
      }

      const fallbackCount = (data.sample_categorized || []).filter(
        t => t.confidence === 'low-fallback'
      ).length
      let msg = `✅ Tải lên thành công! Đã xử lý ${data.rows_inserted} giao dịch từ "${data.filename}".`
      if (fallbackCount > 0) {
        msg += ` (${fallbackCount} giao dịch dùng phân loại dự phòng)`
      }
      setAlert({ type: 'success', msg })
      await fetchData(month)
    } catch (e) {
      setAlert({ type: 'error', msg: e.message || 'Lỗi khi upload file' })
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    handleUploadClick(file)
  }

  /* --- Edit category --- */
  const handleSaveCategory = async (txnId, category) => {
    try {
      const res = await authFetch(`${API_BASE}/transactions/${txnId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category }),
      })
      if (!res.ok) throw new Error('Không thể cập nhật danh mục')
      await fetchData(month)
    } catch (e) {
      setAlert({ type: 'error', msg: e.message })
    }
  }

  /* --- New APIs --- */
  const handleSetBudget = async (category, amount) => {
    try {
      const res = await authFetch(`${API_BASE}/budgets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, amount }),
      })
      if (!res.ok) throw new Error('Không thể lưu ngân sách')
      setAlert({ type: 'success', msg: 'Lưu ngân sách thành công!' })
      await fetchData(month)
    } catch (e) {
      setAlert({ type: 'error', msg: e.message })
    }
  }

  const handleAddTxn = async (data) => {
    try {
      const res = await authFetch(`${API_BASE}/transactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Không thể thêm giao dịch')
      setAlert({ type: 'success', msg: 'Thêm giao dịch thủ công thành công!' })
      await fetchData(month)
    } catch (e) {
      setAlert({ type: 'error', msg: e.message })
    }
  }

  const handleDeleteTxn = async (txnId) => {
    if (!window.confirm('⚠️ Bạn có chắc muốn xóa giao dịch này?')) return
    try {
      const res = await authFetch(`${API_BASE}/transactions/${txnId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Không thể xóa giao dịch')
      await fetchData(month)
    } catch (e) {
      setAlert({ type: 'error', msg: e.message })
    }
  }

  /* --- Clear --- */
  const handleClear = async () => {
    if (!window.confirm('⚠️ Xóa toàn bộ giao dịch? Hành động này không thể hoàn tác!')) return
    setClearing(true)
    try {
      await authFetch(`${API_BASE}/transactions`, { method: 'DELETE' })
      setSummary(null)
      setTxns([])
      setAlert({ type: 'success', msg: 'Đã xóa toàn bộ dữ liệu giao dịch.' })
    } catch {
      setAlert({ type: 'error', msg: 'Lỗi khi xóa dữ liệu' })
    } finally {
      setClearing(false)
    }
  }

  /* --- Derived data --- */
  const byCategory = summary?.by_category
    ? Object.entries(summary.by_category).map(([category, v]) => ({ category, ...v }))
    : []

  const totalSpend  = summary?.total_spend || 0
  const totalIncome = byCategory.find(c => c.category === 'Income')?.total || 0
  const topCat      = summary?.top_3_drivers?.[0]
  const txnCount    = transactions.length

  /* --- Month options (from transactions) --- */
  const months = [...new Set(
    transactions.map(t => t.date?.slice(0, 7)).filter(Boolean).sort().reverse()
  )]

  /* ──── RENDER ──── */
  // Chờ kiểm tra session cũ xong rồi mới render (tránh flicker)
  if (!authChecked) return null

  // Chưa đăng nhập → hiển thị trang Auth
  if (!token) return <AuthPage onAuthenticated={handleAuthenticated} />

  return (
    <div className="app-container">
      {/* ── HEADER ── */}
      <header className="header">
        <div className="header-brand">
          <div className="header-logo">💰</div>
          <div>
            <div className="header-title">BudgetBot</div>
            <div className="header-subtitle">Quản lý ngân sách thông minh với AI</div>
          </div>
        </div>
        <div className="header-actions">
          <span className="header-user-email" title={userEmail}>👤 {userEmail}</span>
          <button
            id="clear-btn"
            className="btn btn-danger btn-sm"
            onClick={handleClear}
            disabled={clearing || txnCount === 0}
            title="Xóa toàn bộ giao dịch"
          >
            {clearing ? <span className="spinner" /> : '🗑️'} Xóa dữ liệu
          </button>
          <button
            id="logout-btn"
            className="btn btn-ghost btn-sm"
            onClick={handleSignOut}
            title="Đăng xuất"
          >
            🚪 Đăng xuất
          </button>
        </div>
      </header>

      {/* ── MAIN ── */}
      <main className="main-content">

        {/* Alert */}
        {alert && (
          <div className={`alert alert-${alert.type}`}>
            <span className="alert-icon">
              {alert.type === 'success' ? '✅' : alert.type === 'warning' ? '⚠️' : '❌'}
            </span>
            <span>{alert.msg}</span>
            <button className="alert-close" onClick={() => setAlert(null)}>✕</button>
          </div>
        )}

        {/* Budget Alerts */}
        {budgetAlerts.map((b_alert, idx) => (
          <div key={idx} className="alert alert-danger budget-alert" style={{ background: 'linear-gradient(135deg, rgba(239,68,68,0.1), rgba(220,38,38,0.2))', border: '1px solid #ef4444' }}>
            <span className="alert-icon">🔥</span>
            <span>
              <strong>CẢNH BÁO NGÂN SÁCH!</strong> Bạn đã chi <strong>{fmtVND(b_alert.spent)}</strong> cho <strong>{CATEGORY_VI[b_alert.category] || b_alert.category}</strong>, vượt quá giới hạn <strong>{fmtVND(b_alert.limit)}</strong>!
            </span>
          </div>
        ))}

        {/* Upload zone */}
        <section className="upload-section">
          <div
            id="upload-zone"
            className={`upload-zone${dragOver ? ' drag-over' : ''}`}
            onClick={() => !uploading && fileRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
          >
            <span className="upload-icon">{uploading ? '⏳' : '📤'}</span>
            <p className="upload-title">
              {uploading ? 'Đang xử lý file...' : 'Tải lên sao kê ngân hàng'}
            </p>
            <p className="upload-desc">
              {uploading
                ? 'AI đang phân loại các giao dịch của bạn...'
                : <>Kéo &amp; thả file vào đây hoặc <span className="upload-browse">chọn file</span> (CSV / PDF)</>
              }
            </p>
            {uploading && (
              <div className="upload-progress">
                <div className="progress-bar-track">
                  <div className="progress-bar-fill" style={{ width: '75%' }} />
                </div>
                <span className="upload-status">Đang gọi AWS Bedrock AI...</span>
              </div>
            )}
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.pdf"
              style={{ display: 'none' }}
              onChange={(e) => handleUploadClick(e.target.files[0])}
              id="file-input"
            />
          </div>
        </section>

        {/* Summary cards */}
        <div className="summary-grid">
          <SummaryCard
            label="Tổng chi tiêu"
            value={fmtVND(Math.abs(totalSpend < 0 ? totalSpend : totalSpend - totalIncome))}
            icon="💸"
            iconBg="rgba(244,63,94,0.15)"
            accent="linear-gradient(135deg,#f43f5e,#ec4899)"
            sub={<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}><span>{txnCount} giao dịch</span><button className="btn btn-ghost btn-sm" style={{padding: '0 4px'}} onClick={() => setShowBudget(true)}>⚙️ Cài đặt</button></div>}
            loading={loading}
          />
          <SummaryCard
            label="Tổng thu nhập"
            value={fmtVND(Math.abs(totalIncome))}
            icon="📈"
            iconBg="rgba(16,185,129,0.15)"
            accent="linear-gradient(135deg,#10b981,#06b6d4)"
            sub="Trong kỳ"
            loading={loading}
          />
          <SummaryCard
            label="Chi nhiều nhất"
            value={topCat ? `${CATEGORY_ICON[topCat.category]} ${CATEGORY_VI[topCat.category]}` : '—'}
            icon="🏆"
            iconBg="rgba(245,158,11,0.15)"
            accent="linear-gradient(135deg,#f59e0b,#f97316)"
            sub={topCat ? fmtFull(Math.abs(topCat.total)) : 'Chưa có dữ liệu'}
            loading={loading}
          />
          <SummaryCard
            label="Số giao dịch"
            value={txnCount.toLocaleString('vi-VN')}
            icon="📋"
            iconBg="rgba(124,58,237,0.15)"
            accent="var(--brand-gradient)"
            sub={month ? `Tháng ${month}` : 'Tất cả thời gian'}
            loading={loading}
          />
        </div>

        {/* Dashboard grid: chart + table */}
        <div className="dashboard-grid">

          {/* Donut chart */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">📊 Chi tiêu theo danh mục</span>
            </div>
            <div className="panel-body" style={{ maxHeight: 450, overflowY: 'auto' }}>
              {loading ? (
                <div className="empty-state">
                  <span className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
                </div>
              ) : (
                <DonutChart data={byCategory} total={totalSpend} />
              )}
            </div>
          </div>

          {/* Trend chart */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">📈 Xu hướng chi tiêu</span>
            </div>
            <div className="panel-body" style={{ height: 450, padding: 0 }}>
              {loading ? (
                <div className="empty-state" style={{ padding: 28 }}>
                  <span className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
                </div>
              ) : summary?.daily_trends?.length > 0 ? (
                <div style={{ width: '100%', height: '100%', overflowX: 'auto', overflowY: 'hidden', padding: 28 }}>
                  <div style={{ minWidth: 600, height: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={summary.daily_trends} margin={{ top: 20, right: 20, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.1)" />
                    <XAxis dataKey="date" tick={{fontSize: 12, fill: '#94a3b8'}} stroke="rgba(255,255,255,0.2)" />
                    <YAxis tickFormatter={(val) => fmtVND(val)} width={60} tick={{fontSize: 12, fill: '#94a3b8'}} stroke="rgba(255,255,255,0.2)" />
                    <Tooltip 
                      formatter={(value) => [fmtFull(value), 'Chi tiêu']} 
                      labelStyle={{color: '#333'}} 
                      contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.2)'}} 
                    />
                    <Bar dataKey="amount" fill="url(#colorUv)" radius={[6, 6, 0, 0]} />
                    <defs>
                      <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ec4899" stopOpacity={0.9}/>
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.9}/>
                      </linearGradient>
                    </defs>
                  </BarChart>
                </ResponsiveContainer>
                  </div>
                </div>
              ) : (
                <div className="empty-state">Chưa có dữ liệu xu hướng</div>
              )}
            </div>
          </div>

          {/* Transactions table */}
          <div className="panel" style={{ gridColumn: '1 / -1' }}>
            <div className="panel-header">
              <span className="panel-title">📋 Danh sách giao dịch</span>
              <div className="filter-bar">
                <button className="btn btn-primary btn-sm" onClick={() => setShowAddTxn(true)}>+ Thêm GD</button>
                <select
                  id="month-filter"
                  className="filter-select"
                  value={month}
                  onChange={(e) => setMonth(e.target.value)}
                >
                  <option value="">Tất cả tháng</option>
                  {months.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => fetchData(month)}
                  disabled={loading}
                  title="Làm mới"
                >
                  {loading ? <span className="spinner" /> : '🔄'}
                </button>
              </div>
            </div>

            <div className="transactions-table-wrapper">
              {loading ? (
                <div className="empty-state">
                  <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
                  <span className="empty-text">Đang tải dữ liệu...</span>
                </div>
              ) : transactions.length === 0 ? (
                <div className="empty-state">
                  <span className="empty-icon">📂</span>
                  <span className="empty-text">Chưa có giao dịch nào. Hãy tải lên sao kê ngân hàng!</span>
                </div>
              ) : (
                <table className="transactions-table" id="transactions-table">
                  <thead>
                    <tr>
                      <th>Ngày</th>
                      <th>Mô tả</th>
                      <th style={{ textAlign: 'right' }}>Số tiền</th>
                      <th>Danh mục</th>
                      <th>Độ tin cậy</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((txn) => (
                      <tr key={txn.id}>
                        <td className="tx-date">{txn.date}</td>
                        <td>
                          <span className="tx-desc" title={txn.description}>
                            {txn.description}
                          </span>
                        </td>
                        <td>
                          <span className={`tx-amount ${txn.amount >= 0 ? 'positive' : 'negative'}`}>
                            {txn.amount >= 0 ? '+' : ''}{fmtVND(txn.amount)}
                          </span>
                        </td>
                        <td>
                          <CategoryBadge category={txn.category} />
                        </td>
                        <td>
                          <span className={`confidence-badge confidence-${txn.confidence || 'low'}`}>
                            {CONFIDENCE_VI[txn.confidence] || '?'}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn-edit"
                            onClick={() => setEditTxn(txn)}
                            title="Sửa danh mục"
                          >
                            ✏️
                          </button>
                          <button
                            className="btn-edit"
                            onClick={() => handleDeleteTxn(txn.id)}
                            title="Xóa giao dịch"
                            style={{marginLeft: 4}}
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer style={{
        textAlign: 'center', padding: '16px', fontSize: '0.75rem',
        color: 'var(--text-muted)', borderTop: '1px solid var(--border)',
      }}>
        BudgetBot · Powered by AWS Bedrock · xBrain Hackathon 2026
      </footer>

      {/* Modals */}
      {showBudget && <BudgetSetupModal budgets={summary?.by_category || {}} onClose={() => setShowBudget(false)} onSave={handleSetBudget} />}
      {showAddTxn && <AddTransactionModal onClose={() => setShowAddTxn(false)} onSave={handleAddTxn} />}
      {csvPreviewData && <CSVPreviewModal previewData={csvPreviewData} onClose={() => {setCsvPreviewData(null); setPendingFile(null)}} onConfirm={(mapping) => {setCsvPreviewData(null); handleUpload(pendingFile, mapping)}} />}

      {/* Edit modal */}
      {editTxn && (
        <EditModal
          txn={editTxn}
          onClose={() => setEditTxn(null)}
          onSave={handleSaveCategory}
        />
      )}

      {/* Floating Chatbot */}
      <Chatbot authFetch={authFetch} CATEGORY_VI={CATEGORY_VI} />
    </div>
  )
}

/* ────────────────────────────────────────────────────────────
   SUMMARY CARD (sub-component)
──────────────────────────────────────────────────────────── */
function SummaryCard({ label, value, icon, iconBg, accent, sub, loading }) {
  return (
    <div className="summary-card" style={{ '--card-accent': accent, '--card-icon-bg': iconBg }}>
      <div className="card-top">
        <span className="card-label">{label}</span>
        <div className="card-icon">{icon}</div>
      </div>
      {loading
        ? <div className="skeleton" style={{ height: 32, width: '70%' }} />
        : <div className="card-value">{value}</div>
      }
      <div className="card-sub">{sub}</div>
    </div>
  )
}

/* ────────────────────────────────────────────────────────────
   CATEGORY BADGE (sub-component)
──────────────────────────────────────────────────────────── */
function CategoryBadge({ category }) {
  const color = CATEGORY_COLOR[category] || '#64748b'
  return (
    <span
      className="cat-badge"
      style={{
        background: `${color}20`,
        color: color,
        borderColor: `${color}40`,
      }}
    >
      {CATEGORY_ICON[category] || '📌'} {CATEGORY_VI[category] || category}
    </span>
  )
}
