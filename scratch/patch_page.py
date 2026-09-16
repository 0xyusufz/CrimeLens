from pathlib import Path

file_path = Path("frontend/app/cases/[caseId]/page.js")
text = file_path.read_text(encoding="utf-8")

old_import = 'import CaseInsightsView from "../../../components/CaseInsightsView";'
new_import = (
    'import CaseInsightsView from "../../../components/CaseInsightsView";\n'
    'import CaseCopilotView from "../../../components/CaseCopilotView";'
)
text = text.replace(old_import, new_import, 1)

old_btn = (
    '              <button\n'
    '                onClick={() => setActiveTab("insights")}\n'
    '                className={`workspace-tab-btn ${activeTab === "insights" ? "tab-btn-active" : ""}`}\n'
    '              >\n'
    '                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">\n'
    '                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />\n'
    '                </svg>\n'
    '                <span>Intelligence</span>\n'
    '              </button>'
)

new_btn = (
    old_btn + '\n\n'
    '              <button\n'
    '                onClick={() => setActiveTab("copilot")}\n'
    '                className={`workspace-tab-btn ${activeTab === "copilot" ? "tab-btn-active" : ""}`}\n'
    '              >\n'
    '                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">\n'
    '                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />\n'
    '                </svg>\n'
    '                <span>AI Copilot & Network</span>\n'
    '              </button>'
)
text = text.replace(old_btn, new_btn, 1)

old_sec = (
    '            {/* TAB 4: INTELLIGENCE / INSIGHTS */}\n'
    '            {activeTab === "insights" && (\n'
    '              <section className="graph-workspace-section">\n'
    '                <CaseInsightsView key={graphRefreshKey} caseId={caseId} />\n'
    '              </section>\n'
    '            )}'
)

new_sec = (
    old_sec + '\n\n'
    '            {/* TAB 5: AI COPILOT & NETWORK */}\n'
    '            {activeTab === "copilot" && (\n'
    '              <section className="graph-workspace-section">\n'
    '                <CaseCopilotView caseId={caseId} />\n'
    '              </section>\n'
    '            )}'
)
text = text.replace(old_sec, new_sec, 1)

file_path.write_text(text, encoding="utf-8")
print("Successfully patched frontend page.js")
