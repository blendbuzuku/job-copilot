import { marked } from 'marked'

/**
 * "Download as PDF": open the document in a clean window and show the print dialog,
 * where the user picks "Save as PDF". No PDF library needed.
 */
export function printAsPdf(title: string, markdown: string) {
  const win = window.open('', '_blank')
  if (!win) return
  win.document.write(`<!doctype html><html><head><title>${title}</title>
    <style>
      body { font: 11pt/1.45 system-ui, sans-serif; max-width: 750px; margin: 32px auto; color: #111; }
      h1 { font-size: 20pt; margin: 0 0 4px; }
      h2 { font-size: 12pt; text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid #ccc; margin-top: 18px; }
      ul { padding-left: 18px; } li { margin: 2px 0; }
    </style></head><body>${marked.parse(markdown, { breaks: true })}</body></html>`)
  win.document.close()
  win.focus()
  win.print()
}
