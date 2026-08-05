# Role A Risk Register

| Risk | Control |
|---|---|
| PDF/DOCX extraction loses structure | Preserve original, quality report, manual Markdown override |
| AI merges unrelated files | AI_PROPOSED state, review required |
| Version inference is wrong | Show evidence and confidence; never auto-supersede low-confidence |
| Large files block server | Size limit, queued normalization, streamed upload |
| B depends on local path | Data Resolve API with job-scoped materialization |
| Restricted data leaks | License policy and public-output filter |
| Context Pack omits frozen contract | Mandatory contract inclusion rule |
