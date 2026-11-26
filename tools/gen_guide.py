"""Builds the Branch Contact Groups action guide (docs/index.html) from the real source files.

Style mirrors the FOE Calendar guide: numbered steps, a Done tick box per step (remembered per guide
version), and collapsed code cards with the Copy button on the page itself. Nothing is hand-copied, so
the pasted code always matches src/*.yaml, docs/formulas.txt and docs/on-start.txt.

Usage: python gen_guide.py [output.html ...]   (default: docs/index.html)
"""
import os, re, html, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..'))
BIBLE = r'C:\Users\Phaderon\Projects\PowerApps'
VERSION = 'v2.50'
KEY = 'bcg-guide-done-' + VERSION + '-r2'

try:
    from zoneinfo import ZoneInfo
    UK = ZoneInfo('Europe/London')
except Exception:  # pragma: no cover
    UK = None


def rd(path):
    return open(path, encoding='utf-8').read().replace('\r\n', '\n').rstrip('\n')


def esc(s):
    return html.escape(s, quote=False)


def stamp(relpath, label):
    """Last commit time of a source file, shown in UK time (real data, never typed in)."""
    out = subprocess.run(['git', 'log', '-1', '--format=%cI', '--', relpath], cwd=REPO, capture_output=True, text=True).stdout.strip()
    if not out:
        return None, label
    dt = datetime.datetime.fromisoformat(out)
    utc = dt.astimezone(datetime.timezone.utc)
    iso = utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    if UK:
        uk = utc.astimezone(UK)
        zone = uk.tzname() or 'GMT'
    else:  # no tz database on this machine: UK rule is last Sunday March 01:00 UTC to last Sunday October 01:00 UTC
        def last_sunday(y, m):
            d = datetime.datetime(y, m, 31, 1, 0, tzinfo=datetime.timezone.utc)
            return d - datetime.timedelta(days=(d.weekday() + 1) % 7)
        bst = last_sunday(utc.year, 3) <= utc < last_sunday(utc.year, 10)
        uk = utc + datetime.timedelta(hours=1 if bst else 0)
        zone = 'BST' if bst else 'GMT'
    return iso, '%s &middot; %s %s' % (label, uk.strftime('%d/%m/%Y %H:%M'), zone)


tpl = open(os.path.join(BIBLE, 'policy-tracker', 'index.html'), encoding='utf-8').read()
CSS = re.search(r'<style>(.*?)</style>', tpl, re.S).group(1)
CSS += """
    .step { display: inline-flex; align-items: center; justify-content: center; min-width: 28px; height: 28px; padding: 0 6px; border-radius: 14px; background: var(--primary); color: #fff; font-weight: 800; margin-right: 8px; }
    table.t { border-collapse: collapse; width: 100%; font-size: .88rem; margin: 10px 0 16px; }
    table.t th, table.t td { border: 1px solid var(--line); padding: 6px 9px; text-align: left; vertical-align: top; }
    table.t th { background: var(--primary-soft); }
    details.code summary { cursor: pointer; padding: 8px 12px; color: #cbd5e1; font-size: .82rem; background: rgba(255,255,255,.05); }
    details.ref { margin: 18px 0; }
    details.ref summary { cursor: pointer; font-weight: 700; padding: 8px 0; }
    .kb { font-family: var(--mono); font-size: .85em; }
    label.done { float: right; font-size: .8rem; font-weight: 600; cursor: pointer; }
    label.done input, ul.ticks input { margin-right: 6px; }
    ul.ticks { list-style: none; padding-left: .2rem; line-height: 2; }
    ul.ticks li.is-done { opacity: .55; text-decoration: line-through; }
    section.is-done h2 { opacity: .55; }
    .replace-all { border: 2px solid var(--primary); border-radius: 12px; padding: 14px 18px; margin: 14px 0 22px; background: var(--primary-soft); }
    .replace-all h2 { margin-top: 0; }
    .replace-all ol { margin: 8px 0 0; padding-left: 1.3rem; line-height: 1.7; }
"""


def card(cid, label, content, ver, relpath, crlf=False, note=''):
    iso, text = stamp(relpath, '')
    when = ''
    if iso:
        when = '<span class="code-stamp" data-updated="%s">%s <span class="code-age"></span></span>' % (iso, text.split('&middot; ', 1)[1])
    stamp_html = when + '<span class="code-stamp">Replace all of it%s</span>' % ((' &mdash; ' + esc(note)) if note else '')
    return '''        <div class="code-card">
          <div class="code-toolbar">
            <div class="code-meta">
              <span>%s</span>
              %s
            </div>
            <button data-copy="%s" data-crlf="%s" type="button">Copy</button>
          </div>
          <details class="code"><summary>Show the code (%s lines)</summary>
<pre id="%s">%s</pre>
          </details>
        </div>
''' % (esc(label), stamp_html, cid, 'true' if crlf else 'false', format(len(content.splitlines()), ','), cid, esc(content))


def done(i):
    return '<label class="done"><input type="checkbox" data-step="%s"> Done</label>' % i


def tick(i, text):
    return '<li><label><input type="checkbox" data-step="%s"> %s</label></li>' % (i, text)


formulas = rd(os.path.join(REPO, 'docs', 'formulas.txt'))
onstart = rd(os.path.join(REPO, 'docs', 'on-start.txt'))
SCR = lambda n: rd(os.path.join(REPO, 'src', n + '.yaml'))

LISTS = [
    ('BM Groups', [
        ('Title', 'Single line of text', 'Group name'),
        ('SortOrder', 'Number', ''),
        ('ThursdayBatch', 'Choice', 'None, Batch 1, Batch 2 (default None)'),
        ('Private', 'Yes/No', 'Default No'),
        ('OfficialSensitiveApproved', 'Yes/No', 'Default No'),
        ('OfficialUseOnly', 'Yes/No', 'Default No'),
        ('Notes', 'Multiple lines of text (plain)', ''),
        ('ManuallySetModified', 'Date and time', 'Optional override of Last modified'),
    ]),
    ('BM Memberships', [
        ('Title', 'Single line of text', 'Mirror of Name'),
        ('Name', 'Single line of text', 'The name the app reads'),
        ('JMC', 'Single line of text', ''),
        ('County/Contingent', 'Single line of text', 'Contains a slash'),
        ('Email', 'Single line of text', 'Lowercase'),
        ('GroupName', 'Single line of text', 'Exactly matches a BM Groups Title (plain text, not a Lookup)'),
        ('Notes', 'Single line of text', ''),
    ]),
    ('BM Maintainers', [
        ('Title', 'Single line of text', 'Name'),
        ('Email', 'Single line of text', 'Lowercase'),
    ]),
    ('BM History', [
        ('Title', 'Single line of text', 'Event description'),
        ('GroupName', 'Single line of text', ''),
        ('EventType', 'Choice', 'Created, Added, Removed, Edited, Replaced'),
    ]),
]


def list_tables():
    out = []
    for name, cols in LISTS:
        out.append('        <h3>%s</h3>\n        <table class="t"><tr><th>Column</th><th>Type</th><th>Notes</th></tr>' % esc(name))
        for c, t, n in cols:
            out.append('<tr><td><span class="kb">%s</span></td><td>%s</td><td>%s</td></tr>' % (esc(c), esc(t), esc(n)))
        out.append('</table>')
    return '\n'.join(out)


SECTIONS = [
    ('formulas', 'Step 1 - App.Formulas'),
    ('onstart', 'Step 2 - App.OnStart'),
    ('delete', 'Step 3 - Delete all screens'),
    ('quick', 'Step 4 - Quick Contacts'),
    ('send', 'Step 5 - Send Email'),
    ('manage', 'Step 6 - Manage Groups'),
    ('import', 'Step 7 - Import (new)'),
    ('people', 'Step 8 - Manage People'),
    ('start', 'Step 9 - Start screen'),
    ('test', 'Step 10 - Test'),
    ('vault', 'Step 11 - Save to the Vault'),
    ('lists', 'SharePoint columns'),
]
nav = '\n'.join('        <a href="#%s">%s</a>' % (i, esc(t)) for i, t in SECTIONS)

def build_time():
    """Time this page was built, in UK time (real clock, never typed in)."""
    utc = datetime.datetime.now(datetime.timezone.utc)
    if UK:
        uk = utc.astimezone(UK)
        zone = uk.tzname() or 'GMT'
    else:
        def last_sunday(y, m):
            d = datetime.datetime(y, m, 31, 1, 0, tzinfo=datetime.timezone.utc)
            return d - datetime.timedelta(days=(d.weekday() + 1) % 7)
        bst = last_sunday(utc.year, 3) <= utc < last_sunday(utc.year, 10)
        uk = utc + datetime.timedelta(hours=1 if bst else 0)
        zone = 'BST' if bst else 'GMT'
    return '%s %s' % (uk.strftime('%d/%m/%Y %H:%M'), zone)

BODY = '''
      <div class="topline">
        <span class="pill">%(ver)s</span>
        <span class="pill">Last build %(stamp)s</span>
      </div>
      <h1>Branch Contact Groups</h1>
      <div class="replace-all">
        <h2>Replace everything</h2>
        <p>Everything below is new compared with the app in Studio. Do not pick and choose. Work down the page and tick each step off. Copy works without opening the code.</p>
        <ol>
          <li>Replace <strong>App.Formulas</strong> and <strong>App.OnStart</strong></li>
          <li>Delete <strong>all five screens</strong></li>
          <li>Paste all five back: Quick Contacts, Send Email, Manage Groups, Import, Manage People</li>
        </ol>
      </div>

      <section id="formulas">
        <h2><span class="step">1</span>App.Formulas %(d_formulas)s</h2>
        <p>Select <strong>App</strong> &rarr; <span class="kb">Formulas</span>, replace everything, paste.</p>
%(c_formulas)s
      </section>

      <section id="onstart">
        <h2><span class="step">2</span>App.OnStart %(d_onstart)s</h2>
        <p>Select <strong>App</strong> &rarr; <span class="kb">OnStart</span>, replace everything, paste.</p>
%(c_onstart)s
      </section>

      <section id="delete">
        <h2><span class="step">3</span>Delete all five screens %(d_delete)s</h2>
        <p>In the Tree view, delete <span class="kb">scrQuickContacts</span>, <span class="kb">scrSendEmail</span>, <span class="kb">scrManageGroups</span>, <span class="kb">scrManagePeople</span> and <span class="kb">scrImport</span> if it exists. Pasting does not overwrite, so old copies would be duplicated. Red errors on the screens you paste first are normal until all five are in.</p>
      </section>

      <section id="quick">
        <h2><span class="step">4</span>scrQuickContacts %(d_quick)s</h2>
        <p>Add a blank screen named exactly <span class="kb">scrQuickContacts</span>, then paste.</p>
%(c_quick)s
      </section>

      <section id="send">
        <h2><span class="step">5</span>scrSendEmail %(d_send)s</h2>
        <p>Add a blank screen named exactly <span class="kb">scrSendEmail</span>, then paste.</p>
%(c_send)s
      </section>

      <section id="manage">
        <h2><span class="step">6</span>scrManageGroups %(d_manage)s</h2>
        <p>Add a blank screen named exactly <span class="kb">scrManageGroups</span>, then paste. (It has the <strong>Import from paste</strong> button, A to Z sorting, and a progress bar when you rename a group.)</p>
%(c_manage)s
      </section>

      <section id="import">
        <h2><span class="step">7</span>scrImport (new) %(d_import)s</h2>
        <p>Add a blank screen named exactly <span class="kb">scrImport</span>, then paste. If a <span class="kb">Navigate</span> on Manage Groups shows red until this exists, that is expected.</p>
%(c_import)s
      </section>

      <section id="people">
        <h2><span class="step">8</span>scrManagePeople %(d_people)s</h2>
        <p>Add a blank screen named exactly <span class="kb">scrManagePeople</span>, then paste. The code is unchanged apart from the version label being removed.</p>
%(c_people)s
      </section>

      <section id="start">
        <h2><span class="step">9</span>Start screen %(d_start)s</h2>
        <p>Select <strong>App</strong>, set <span class="kb">StartScreen</span> to <span class="kb">scrQuickContacts</span>, save.</p>
      </section>

      <section id="test">
        <h2><span class="step">10</span>Test</h2>
        <ul class="ticks">
          %(t1)s
          %(t2)s
          %(t3)s
          %(t4)s
          %(t5)s
          %(t6)s
          %(t7)s
          %(t8)s
          %(t9)s
          %(t10)s
          %(t11)s
        </ul>
      </section>

      <section id="vault">
        <h2><span class="step">11</span>Save to the Vault %(d_vault)s</h2>
        <p>Save all five screens and App.OnStart back into the <a href="yaml.html">Screen YAML Vault</a>, then tell me, so I can check what is really in the app.</p>
      </section>

      <details class="ref" id="lists">
        <summary>SharePoint columns (already built, for reference)</summary>
        <p>Every column is <strong>Not Required</strong>. No list changes this round.</p>
%(lists)s
      </details>
''' % {
    'ver': VERSION, 'stamp': build_time(),
    'd_formulas': done('formulas'), 'd_delete': done('delete'), 'd_onstart': done('onstart'), 'd_quick': done('quick'), 'd_send': done('send'),
    'd_manage': done('manage'), 'd_import': done('import'), 'd_people': done('people'), 'd_start': done('start'), 'd_vault': done('vault'),
    'c_formulas': card('bcg-formulas', 'App - Formulas', formulas, 'v2.49', 'docs/formulas.txt'),
    'c_onstart': card('bcg-onstart', 'App - OnStart', onstart, 'v2.49', 'docs/on-start.txt'),
    'c_quick': card('bcg-quick', 'Screen - scrQuickContacts', SCR('scrQuickContacts'), 'v2.49', 'src/scrQuickContacts.yaml', crlf=True),
    'c_send': card('bcg-send', 'Screen - scrSendEmail', SCR('scrSendEmail'), 'v2.49', 'src/scrSendEmail.yaml', crlf=True),
    'c_manage': card('bcg-manage', 'Screen - scrManageGroups', SCR('scrManageGroups'), 'v2.50', 'src/scrManageGroups.yaml', crlf=True),
    'c_import': card('bcg-import', 'Screen - scrImport', SCR('scrImport'), 'v2.50', 'src/scrImport.yaml', crlf=True, note='new'),
    'c_people': card('bcg-people', 'Screen - scrManagePeople', SCR('scrManagePeople'), 'v2.48', 'src/scrManagePeople.yaml', crlf=True),
    't1': tick('t1', 'Open the app: a loading screen, then the list. Note how many seconds it takes.'),
    't2': tick('t2', 'Quick Contacts: <strong>Who\'s in it</strong> opens a popup with the members, and Copy addresses works.'),
    't3': tick('t3', 'Send Email: tick a group of cadetnet addresses. BCC is not forced.'),
    't4': tick('t4', 'Manage Groups &rarr; <strong>Import from paste</strong> opens the Import screen.'),
    't5': tick('t5', 'Import: paste 3 or 4 made-up lines (for example <span class="kb">TEST: Role One alex@example.test; Role Two sam@example.test</span>), Check paste, name it, Import. Delete the test group afterwards.'),
    't8': tick('t8', 'Import: switch to <strong>Replace whole group</strong> or <strong>Add and correct emails</strong>. Each list now shows a dropdown of your existing groups instead of a text box. Pick the group, check the status line, then Import.'),
    't11': tick('t11', 'Last-updated date: on Import (next to Import now) and on Manage Members &rarr; Replace all, tick <strong>Set the last-updated date</strong>, pick a date, run it. The group card then shows that date. Left unticked, the date is not touched.'),
    't10': tick('t10', 'Manage Groups: Edit group, type a note over several lines (Enter for a new line), Save. That group card now shows an amber <strong>Note</strong> chip. Hover shows the note; click opens a popup with Edit group and Close.'),
    't9': tick('t9', 'Manage Groups &rarr; a group &rarr; Manage Members &rarr; <strong>Replace all (CSV / Outlook)</strong>: choose <strong>From Outlook</strong>, paste an Outlook list, check the counts, then Replace. <strong>From CSV / Excel</strong> works as before.'),
    't7': tick('t7', 'Manage Groups: edit a group, change its name, Save. A box appears with a progress bar counting up, then a green Saved message. Groups are listed A to Z.'),
    't6': tick('t6', 'Import: the real lists, only after the test worked.'),
    'lists': list_tables(),
}

SCRIPTS = r'''
  <script>
  (function () {
    var K = '%(key)s';
    var saved = {};
    try { saved = JSON.parse(localStorage.getItem(K) || '{}'); } catch (e) {}
    document.querySelectorAll('input[data-step]').forEach(function (cb) {
      var id = cb.getAttribute('data-step'), sec = cb.closest('li') || cb.closest('section');
      cb.checked = !!saved[id]; sec.classList.toggle('is-done', cb.checked);
      cb.addEventListener('change', function () {
        saved[id] = cb.checked; sec.classList.toggle('is-done', cb.checked);
        try { localStorage.setItem(K, JSON.stringify(saved)); } catch (e) {}
      });
    });
  })();
  </script>
  <script>
  (function () {
    document.querySelectorAll('button[data-copy]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var el = document.getElementById(btn.getAttribute('data-copy'));
        var text = el.textContent;
        if (btn.getAttribute('data-crlf') === 'true') text = text.replace(/\r?\n/g, '\r\n');
        function ok() { var o = btn.textContent; btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = o; }, 1500); }
        function fallback() {
          var ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
          document.body.appendChild(ta); ta.select();
          try { document.execCommand('copy'); ok(); } catch (e) { btn.textContent = 'Copy failed'; }
          document.body.removeChild(ta);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(text).then(ok, fallback); } else { fallback(); }
      });
    });
  })();
  </script>
  <script>
  (function () {
    var navLinks = Array.from(document.querySelectorAll('nav a[href^="#"]'));
    var sections = navLinks.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); }).filter(Boolean);
    if (!sections.length || !('IntersectionObserver' in window)) return;
    function setActive(id) { navLinks.forEach(function (a) { a.classList.toggle('active', a.getAttribute('href') === '#' + id); }); }
    var observer = new IntersectionObserver(function (entries) {
      var visible = entries.filter(function (e) { return e.isIntersecting; });
      if (visible.length === 0) return;
      visible.sort(function (a, b) { return a.boundingClientRect.top - b.boundingClientRect.top; });
      setActive(visible[0].target.id);
    }, { rootMargin: '-15%% 0px -70%% 0px', threshold: 0 });
    sections.forEach(function (s) { observer.observe(s); });
  })();
  </script>
  <script>
  (function () {
    function age(ms) {
      var m = Math.floor(ms / 60000);
      if (m < 1) return 'just now';
      if (m < 120) return m + ' minute' + (m === 1 ? '' : 's') + ' ago';
      var h = Math.floor(m / 60);
      if (h < 48) return h + ' hours ago';
      return Math.floor(h / 24) + ' days ago';
    }
    function refresh() {
      var now = Date.now();
      document.querySelectorAll('.code-stamp[data-updated]').forEach(function (el) {
        var t = new Date(el.getAttribute('data-updated')).getTime();
        var out = el.querySelector('.code-age');
        if (isNaN(t) || !out) return;
        out.textContent = '(' + age(Math.max(0, now - t)) + ')';
      });
    }
    refresh();
    setInterval(refresh, 30000);
  })();
  </script>
''' % {'key': KEY}

THEME = re.search(r'<button id="theme-toggle".*?</script>', tpl, re.S).group(0)

PAGE = '''<!DOCTYPE html>
<html lang="en-GB">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Branch Contact Groups - Build Guide</title>
  <style>%s</style>
</head>
<body>
  %s
  <div class="shell">
    <aside>
      <h2>Branch Contact Groups</h2>
      <p>Paste, tick off, test.</p>
      <nav>
        <a href="https://powerapps.pages.dev/">Guide library</a>
%s
        <a href="yaml.html">Screen YAML Vault</a>
      </nav>
    </aside>

    <main>
%s
    </main>
  </div>
%s
</body>
</html>
''' % (CSS, THEME, nav, BODY, SCRIPTS)

outs = sys.argv[1:] or [os.path.join(REPO, 'docs', 'index.html')]
for o in outs:
    os.makedirs(os.path.dirname(os.path.abspath(o)), exist_ok=True)
    open(o, 'w', encoding='utf-8', newline='\n').write(PAGE)
    print('wrote', o, len(PAGE), 'bytes')
