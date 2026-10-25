Salah Archive v15.81 - Virtual Server Schema Parser Fix

What changed:
- Fixed MySQL schema preflight index parser to correctly parse nested index-prefix syntax such as INDEX idx_local_docs_subject (subject(191)).
- This was a parser bug: the candidate schema explicitly expects subject(191), but the preflight parser previously truncated at the inner ')' and incorrectly reported subject with no prefix.
- No database was accessed or altered while making this fix.
- The production database remains protected by the existing database guard.
- The existing test database is NOT automatically dropped, altered, or recreated by this fix.

Validation:
- 164 unit tests pass.
- Integrity guard passes.
- Candidate schema parser now reports idx_local_docs_subject as (subject, prefix 191).
- Live MySQL integration has NOT yet been rerun; run TEST_VIRTUAL_SERVER_MYSQL.bat and inspect MYSQL_LIVE_INTEGRATION_RESULT_SERVER.json.
