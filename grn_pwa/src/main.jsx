import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import PWA from "./PWA.jsx"
import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <PWA />
  </StrictMode>,
)
