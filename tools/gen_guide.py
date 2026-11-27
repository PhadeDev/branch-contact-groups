"""Builds the Branch Contact Groups update guide (docs/index.html) from the real source files.

One page, one flow: Part 1 SharePoint, Part 2 Power Apps Studio, Part 3 Test, Part 4 Save.
Every step has a big status pill worked out in the browser from real data:
  green  = new or changed since you last ticked it  (do it now)
  amber  = not ticked and a while old                (still to do, or tick if you already did it)
  grey   = ticked after the last change              (done)
The change times are the real git commit times of the source files. Nothing is typed in by hand.

Usage: python gen_guide.py [output.html ...]   (default: docs/index.html)
"""
import os, html, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..'))
VERSION = 'v3.0'
KEY = 'bcg-guide-v3'

try:
    from zoneinfo import ZoneInfo
    UK = ZoneInfo('Europe/London')
except Exception:  # pragma: no cover
    UK = None


def rd(path):
    return open(path, encoding='utf-8').read().replace('\r\n', '\n').rstrip('\n')


def esc(s):
    return html.escape(s, quote=False)


def to_uk(utc):
    if UK:
        uk = utc.astimezone(UK)
        return uk, (uk.tzname() or 'GMT')

    def last_sunday(y, m):
        d = datetime.datetime(y, m, 31, 1, 0, tzinfo=datetime.timezone.utc)
        return d - datetime.timedelta(days=(d.weekday() + 1) % 7)
    bst = last_sunday(utc.year, 3) <= utc < last_sunday(utc.year, 10)
    return utc + datetime.timedelta(hours=1 if bst else 0), ('BST' if bst else 'GMT')


def git_time(args):
    """Latest commit time (UTC datetime) for a git log query, or None."""
    out = subprocess.run(['git', 'log', '-1', '--format=%cI'] + args, cwd=REPO, capture_output=True, text=True).stdout.strip()
    if not out:
        return None
    return datetime.datetime.fromisoformat(out).astimezone(datetime.timezone.utc)


def uk_text(utc):
    uk, zone = to_uk(utc)
    return '%s %s' % (uk.strftime('%d/%m/%Y %H:%M'), zone)


def iso(utc):
    return utc.strftime('%Y-%m-%dT%H:%M:%SZ')


FILES = {
    'formulas': 'docs/formulas.txt',
    'onstart': 'docs/on-start.txt',
    'quick': 'src/scrQuickContacts.yaml',
    'send': 'src/scrSendEmail.yaml',
    'manage': 'src/scrManageGroups.yaml',
    'import': 'src/scrImport.yaml',
    'people': 'src/scrManagePeople.yaml',
}
T = {k: git_time(['--', v]) for k, v in FILES.items()}
T_SCREENS = max(T[k] for k in ('quick', 'send', 'manage', 'import', 'people'))
T_SP = git_time(['-S', 'HasCustodians', '--', 'src/scrManageGroups.yaml']) or T_SCREENS
NOW = datetime.datetime.now(datetime.timezone.utc)

formulas = rd(os.path.join(REPO, 'docs', 'formulas.txt'))
onstart = rd(os.path.join(REPO, 'docs', 'on-start.txt'))
SCR = lambda n: rd(os.path.join(REPO, 'src', n + '.yaml'))


def code_card(cid, label, content, crlf=False):
    return '''
        <div class="code-card">
          <button class="copy-big" data-copy="%s" data-crlf="%s" type="button">Copy the code for %s</button>
          <details class="code"><summary>Show the code (%s lines). You do not need to open this.</summary>
<pre id="%s">%s</pre>
          </details>
        </div>
''' % (cid, 'true' if crlf else 'false', esc(label), format(len(content.splitlines()), ','), cid, esc(content))


def copy_text(text):
    return '<button class="copy-small" type="button" data-text="%s">Copy</button>' % html.escape(text, quote=True)


def name_row(name, desc):
    return '<div class="namerow"><span class="kb">%s</span> %s <span class="desc">%s</span></div>' % (esc(name), copy_text(name), desc)


# ---------------------------------------------------------------------------------------------
# The steps, in the order you do them
# ---------------------------------------------------------------------------------------------
STEPS = []


def step(sid, part, title, where, changed, kind, body, code='', needed=''):
    STEPS.append(dict(id=sid, part=part, title=title, where=where, changed=changed, kind=kind, body=body, code=code, needed=needed))


step('sp1', 1, 'Add two new columns to the BM Groups list', 'In your web browser, on SharePoint', T_SP, 'change', '''
          <p class="lead">This is the part that is easy to miss, so it is first. The new screens need two new columns. Without them the screens show red errors.</p>
          <ol class="how">
            <li>Open SharePoint and go to <strong>Site contents</strong>. Click the list called <strong>BM Groups</strong>.</li>
            <li>At the far right of the column headings, click <strong>+ Add column</strong>, then choose <strong>Yes/No</strong>.</li>
            <li>Name it exactly: ''' + name_row('HasCustodians', '') + ''' Set <strong>Default value</strong> to <strong>No</strong>, then click <strong>Save</strong>.</li>
            <li>Click <strong>+ Add column</strong> again, then choose <strong>Multiple lines of text</strong>.</li>
            <li>Name it exactly: ''' + name_row('CustodianEmails', '') + ''' Open <strong>More options</strong> and make sure <strong>Use enhanced rich text</strong> is <strong>off</strong>. Click <strong>Save</strong>.</li>
          </ol>
          <p class="warn">Spell both names exactly as shown, capital letters and no spaces. Use the Copy buttons.</p>
''', needed='Yes, this round')

step('sp2', 1, 'Check the Email column is not "Required"', 'In your web browser, on SharePoint', T_SP, 'change', '''
          <p class="lead">Some groups will now have members with no email address. SharePoint must allow that.</p>
          <ol class="how">
            <li>Go back to <strong>Site contents</strong> and open the list <strong>BM Memberships</strong>.</li>
            <li>Click the heading of the <strong>Email</strong> column, then <strong>Column settings</strong>, then <strong>Edit</strong>.</li>
            <li>Open <strong>More options</strong>. Make sure <strong>Require that this column contains information</strong> is set to <strong>No</strong>.</li>
            <li>Click <strong>Save</strong>. If it was already No, just click Cancel.</li>
          </ol>
''', needed='Yes, this round')

step('studio1', 2, 'Refresh the BM Groups data source in Power Apps Studio', 'In Power Apps Studio (the editor for the app)', T_SP, 'change', '''
          <p class="lead">Studio does not notice new columns by itself. You have to tell it.</p>
          <ol class="how">
            <li>Open the app in <strong>Power Apps Studio</strong> for editing.</li>
            <li>On the far left, click the <strong>Data</strong> icon (it looks like a small database).</li>
            <li>Find <strong>BM Groups</strong>, click the <strong>three dots</strong> next to it, then click <strong>Refresh</strong>.</li>
            <li>Wait for it to finish. You should now see <span class="kb">HasCustodians</span> and <span class="kb">CustodianEmails</span> if you expand the list.</li>
          </ol>
''', needed='Yes, this round')

step('formulas', 2, 'Replace App.Formulas', 'Power Apps Studio, then App, then Formulas', T['formulas'], 'change', '''
          <ol class="how">
            <li>In the Tree view on the left, click <strong>App</strong>. In the property list at the top choose <strong>Formulas</strong>.</li>
            <li>Select everything in the formula box and delete it.</li>
            <li>Click the big green Copy button below, then paste.</li>
          </ol>
''', code=code_card('bcg-formulas', 'App.Formulas', formulas), needed='formulas')

step('onstart', 2, 'Replace App.OnStart', 'Power Apps Studio, then App, then OnStart', T['onstart'], 'change', '''
          <ol class="how">
            <li>In the Tree view, click <strong>App</strong>. In the property list at the top choose <strong>OnStart</strong>.</li>
            <li>Select everything and delete it.</li>
            <li>Click the big green Copy button below, then paste.</li>
          </ol>
''', code=code_card('bcg-onstart', 'App.OnStart', onstart), needed='onstart')

step('delete', 2, 'Delete all five old screens', 'Power Apps Studio, Tree view', T_SCREENS, 'change', '''
          <p class="lead">Pasting adds screens, it never replaces them. If the old ones stay you get duplicates.</p>
          <ol class="how">
            <li>In the Tree view, delete these five screens one at a time (click the three dots, then <strong>Delete</strong>):</li>
          </ol>
          <ul class="chips"><li>scrQuickContacts</li><li>scrSendEmail</li><li>scrManageGroups</li><li>scrManagePeople</li><li>scrImport</li></ul>
          <p>Red errors appearing while you do this and the next five steps are normal. They clear once all five are pasted.</p>
''', needed='Yes, this round')


def screen_step(sid, name, key, extra='', changed=None):
    step(sid, 2, 'Paste %s' % name, 'Power Apps Studio, Tree view', changed or T[key], 'change', '''
          <ol class="how">
            <li>Click <strong>+ New screen</strong>, then <strong>Blank</strong>.</li>
            <li>Rename it exactly <span class="kb">%s</span> (three dots, <strong>Rename</strong>).</li>
            <li>Click the big green Copy button below. Click the empty screen, then press <span class="kb">Ctrl</span> + <span class="kb">V</span>.</li>
          </ol>
%s''' % (name, extra), code=code_card('bcg-' + key, name, SCR(name), crlf=True), needed='screen')


screen_step('s_quick', 'scrQuickContacts', 'quick')
screen_step('s_send', 'scrSendEmail', 'send')
screen_step('s_manage', 'scrManageGroups', 'manage')
screen_step('s_import', 'scrImport', 'import')
screen_step('s_people', 'scrManagePeople', 'people')

step('start', 2, 'Check the start screen', 'Power Apps Studio, App properties', None, 'check', '''
          <ol class="how">
            <li>Click <strong>App</strong> in the Tree view. Look at <strong>StartScreen</strong>.</li>
            <li>It should say <span class="kb">scrQuickContacts</span>. If it does not, set it, then save.</li>
          </ol>
''', needed='Quick check')

TESTS = [
    ('t1', 'Open the app. You see a loading screen, then the list of groups.'),
    ('t2', 'Quick Contacts: <strong>Who&rsquo;s in it</strong> opens a popup with the members, and Copy addresses works.'),
    ('t3', 'Send Email: tick a group of cadetnet addresses. BCC is not forced.'),
    ('t4', 'Send Email: tick a group with an outside address. You see the new BCC message about non-MODNET addresses.'),
    ('t5', 'Every screen has a <strong>Home</strong> button that goes to Quick Contacts. Send Email also has Back.'),
    ('t6', 'Manage Groups: edit a group, change its name, Save. A progress bar counts up, then <strong>one</strong> green Saved message.'),
    ('t7', 'Manage Groups: edit a group, tick <strong>Add custodians</strong>, search by surname, Add two people, Save.'),
    ('t8', 'Open that group from Quick Contacts and from Send Email. The amber notice and the custodians (photo, name, email) show above the members.'),
    ('t9', 'In that group, Manage Members: add a person and leave the email empty. It saves. In Send Email that person is ignored and the count says how many have no email.'),
    ('t10', 'Import: paste 3 or 4 made-up lines such as <span class="kb">TEST: Role One alex@example.test; Role Two sam@example.test</span>, Check paste, Import. Delete the test group afterwards.'),
    ('t11', 'Manage Groups, Manage Members, <strong>Replace all (CSV / Outlook)</strong>: replace, then the box closes, you see a green Saved, and the list refreshes by itself.'),
    ('t12', 'Edit a group, type a note over several lines, Save. The group card shows an amber <strong>Note</strong> chip.'),
]
tests_html = '<ul class="ticks">' + ''.join(
    '<li><label><input type="checkbox" data-tick="%s"> <span>%s</span></label></li>' % (i, t) for i, t in TESTS) + '</ul>'
step('test', 3, 'Test it', 'In the app itself', None, 'late', '''
          <p class="lead">Tick each line as it works. If one does not work, take a screenshot and tell me which line.</p>
''' + tests_html, needed='After pasting')

step('vault', 4, 'Save the screens back to the Vault', 'Power Apps Studio, then the Vault page', None, 'late', '''
          <ol class="how">
            <li>Save the app in Studio.</li>
            <li>Save all five screens and App.OnStart into the <a href="yaml.html">Screen YAML Vault</a>, then tell me, so I can check what is really in the app.</li>
          </ol>
''', needed='Last')

PARTS = {
    1: ('PART 1', 'SharePoint', 'In your web browser. Two columns to add and one setting to check.', '#13284C'),
    2: ('PART 2', 'Power Apps Studio', 'In the app editor. Refresh, replace, delete, paste.', '#153E35'),
    3: ('PART 3', 'Test', 'Open the app and check it works.', '#8E1537'),
    4: ('PART 4', 'Save', 'Tell me when it is done.', '#323E48'),
}

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
        ('HasCustodians', 'Yes/No', 'NEW. Default No'),
        ('CustodianEmails', 'Multiple lines of text (plain)', 'NEW. Semicolon-separated email addresses'),
    ]),
    ('BM Memberships', [
        ('Title', 'Single line of text', 'Mirror of Name'),
        ('Name', 'Single line of text', 'The name the app reads'),
        ('JMC', 'Single line of text', ''),
        ('County/Contingent', 'Single line of text', 'Contains a slash'),
        ('Email', 'Single line of text', 'Lowercase. Must NOT be Required'),
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
        out.append('<h3>%s</h3><table class="t"><tr><th>Column</th><th>Type</th><th>Notes</th></tr>' % esc(name))
        for c, t, n in cols:
            out.append('<tr><td><span class="kb">%s</span></td><td>%s</td><td>%s</td></tr>' % (esc(c), esc(t), esc(n)))
        out.append('</table>')
    return '\n'.join(out)


def render_step(n, st):
    ch = ''
    chattr = ''
    if st['changed']:
        chattr = ' data-changed="%s"' % iso(st['changed'])
        ch = '<div class="changed">Last changed <strong>%s</strong> <span class="age"></span></div>' % uk_text(st['changed'])
    needed = st['needed']
    note = ''
    if needed == 'formulas' or needed == 'onstart':
        note = '<div class="skipnote">Not changed since <strong>%s</strong>. If you already pasted it on or after that date, skip this step and tick it done.</div>' % uk_text(st['changed'])
    return '''
      <article class="step" id="%s" data-id="%s" data-kind="%s"%s>
        <header>
          <div class="num">%d</div>
          <div class="title"><h3>%s</h3><div class="where">%s</div></div>
          <div class="pill" data-pill>&nbsp;</div>
        </header>
        %s
        %s
        <div class="body">%s%s</div>
        <button class="donebtn" type="button" data-done>I have done this step</button>
      </article>
''' % (st['id'], st['id'], st['kind'], chattr, n, st['title'], esc(st['where']), ch, note, st['body'], st['code'])


# ---------------------------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------------------------
parts_html = []
n = 0
last_part = None
for st in STEPS:
    n += 1
    if st['part'] != last_part:
        last_part = st['part']
        lab, name, sub, col = PARTS[st['part']]
        parts_html.append('''
      <div class="part" style="--pc:%s" id="part%d">
        <div class="part-label">%s</div>
        <div class="part-name">%s</div>
        <div class="part-sub">%s</div>
      </div>
''' % (col, st['part'], lab, name, sub))
    parts_html.append(render_step(n, st))

road = ''.join('<li><a href="#%s"><span class="rn" style="background:%s">%d</span> %s</a></li>' % (
    st['id'], PARTS[st['part']][3], i + 1, esc(st['title'])) for i, st in enumerate(STEPS))

fdays = (NOW - T['formulas']).days

PAGE = '''<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Branch Contact Groups - Update Guide</title>
<style>
:root {
  --purple: #532A45; --grey: #323E48; --blue: #13284C; --green: #153E35; --yellow: #F6A800; --orange: #E0592B; --pink: #8E1537;
  --bg: #F7F4F6; --card: #FFFFFF; --soft: #F0ECF0; --line: #D0C4CC; --muted: #4B5866;
  --go: #1E7B3A; --wait: #F6A800; --done: #4B5866;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 130px; }
body { margin: 0; background: var(--bg); color: var(--grey); font-family: "Open Sans", Segoe UI, Arial, sans-serif; font-size: 20px; line-height: 1.6; }
a { color: var(--blue); font-weight: 700; }
a:focus-visible, button:focus-visible, input:focus-visible, summary:focus-visible { outline: 4px solid var(--yellow); outline-offset: 3px; }
.band { background: var(--purple); color: #fff; padding: 28px 20px 24px; }
.wrap { max-width: 980px; margin: 0 auto; padding: 0 16px; }
.band h1 { margin: 0 0 6px; font-size: 40px; line-height: 1.2; }
.band p { margin: 4px 0; font-size: 22px; }
.band .built { font-size: 20px; opacity: .95; }
.band .links { margin-top: 14px; display: flex; gap: 12px; flex-wrap: wrap; }
.band .links a { color: #fff; background: rgba(255,255,255,.16); border: 2px solid rgba(255,255,255,.6); border-radius: 30px; padding: 8px 20px; text-decoration: none; }
.sticky { position: sticky; top: 0; z-index: 20; background: #fff; border-bottom: 4px solid var(--purple); box-shadow: 0 3px 10px rgba(0,0,0,.12); }
.sticky .wrap { display: flex; align-items: center; gap: 16px; padding-top: 10px; padding-bottom: 10px; flex-wrap: wrap; }
.prog { flex: 1 1 260px; }
.prog .txt { font-weight: 800; font-size: 22px; }
.bar { height: 16px; background: var(--soft); border-radius: 10px; overflow: hidden; border: 1px solid var(--line); }
.bar > i { display: block; height: 100%; width: 0; background: var(--go); transition: width .4s; }
.nextbtn { background: var(--go); color: #fff; border: 0; border-radius: 12px; font-size: 22px; font-weight: 800; padding: 12px 22px; cursor: pointer; min-height: 52px; }
.nextbtn:hover { background: #17642F; }
.short { background: #fff; border: 4px solid var(--purple); border-radius: 16px; padding: 20px 24px; margin: 26px 0; }
.short h2 { margin: 0 0 8px; font-size: 30px; color: var(--purple); }
.short ul { margin: 8px 0 0; padding-left: 1.3em; }
.short li { margin: 6px 0; }
.roadmap { background: #fff; border: 2px solid var(--line); border-radius: 16px; padding: 18px 24px; margin: 0 0 30px; }
.roadmap h2 { margin: 0 0 8px; font-size: 28px; }
.roadmap ol { list-style: none; padding: 0; margin: 0; columns: 1; }
.roadmap li { margin: 4px 0; }
.roadmap a { text-decoration: none; display: block; padding: 6px 4px; border-radius: 8px; }
.roadmap a:hover { background: var(--soft); }
.rn { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 50%; color: #fff; font-weight: 800; margin-right: 8px; }
.part { background: var(--pc); color: #fff; border-radius: 16px; padding: 18px 26px; margin: 46px 0 18px; }
.part-label { font-size: 20px; letter-spacing: .12em; font-weight: 800; opacity: .9; }
.part-name { font-size: 40px; font-weight: 800; line-height: 1.15; }
.part-sub { font-size: 22px; margin-top: 4px; }
.step { background: var(--card); border: 2px solid var(--line); border-left: 14px solid var(--wait); border-radius: 16px; padding: 22px 26px 26px; margin: 0 0 24px; }
.step.s-go { border-left-color: var(--go); }
.step.s-wait { border-left-color: var(--wait); }
.step.s-done { border-left-color: var(--done); background: #F3F1F3; }
.step.s-done .body { display: none; }
.step.s-done .changed, .step.s-done .skipnote { display: none; }
.step header { display: flex; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
.num { width: 64px; height: 64px; border-radius: 50%; background: var(--purple); color: #fff; font-size: 34px; font-weight: 800; display: flex; align-items: center; justify-content: center; flex: 0 0 auto; }
.title { flex: 1 1 320px; }
.title h3 { margin: 0; font-size: 30px; line-height: 1.25; }
.where { font-size: 20px; color: var(--muted); font-weight: 600; margin-top: 2px; }
.pill { font-size: 22px; font-weight: 800; border-radius: 40px; padding: 10px 22px; white-space: normal; text-align: center; line-height: 1.25; max-width: 100%; }
.pill.p-go { background: var(--go); color: #fff; }
.pill.p-wait { background: var(--wait); color: #1b1b1b; }
.pill.p-done { background: var(--done); color: #fff; }
.pill.p-check { background: var(--blue); color: #fff; }
.pill.p-late { background: var(--soft); color: var(--grey); border: 2px solid var(--line); }
.changed { font-size: 22px; margin: 16px 0 4px; padding: 10px 16px; background: var(--soft); border-radius: 10px; }
.changed strong { font-size: 24px; }
.age { font-weight: 800; }
.skipnote { font-size: 22px; margin: 10px 0 0; padding: 12px 16px; border: 3px solid var(--yellow); background: #FFF6DD; border-radius: 10px; }
.lead { font-size: 22px; font-weight: 600; }
.how { padding-left: 1.6em; margin: 14px 0; }
.how li { margin: 12px 0; padding-left: 6px; }
.how li::marker { font-weight: 800; color: var(--purple); font-size: 1.1em; }
.warn { background: #FFF6DD; border: 3px solid var(--yellow); border-radius: 10px; padding: 12px 16px; font-weight: 700; }
.kb { font-family: Consolas, Menlo, monospace; background: var(--soft); border: 1px solid var(--line); border-radius: 6px; padding: 1px 8px; font-size: .95em; font-weight: 700; }
.namerow { display: inline-flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 4px 0; }
.namerow .kb { font-size: 1.15em; }
.copy-small { background: var(--blue); color: #fff; border: 0; border-radius: 8px; font-size: 18px; font-weight: 800; padding: 6px 16px; cursor: pointer; min-height: 40px; }
.copy-big { display: block; width: 100%; background: var(--go); color: #fff; border: 0; border-radius: 14px; font-size: 26px; font-weight: 800; padding: 18px 20px; cursor: pointer; min-height: 70px; }
.copy-big:hover { background: #17642F; }
.copy-big.copied, .copy-small.copied { background: var(--purple); }
.code-card { margin: 18px 0 0; }
details.code { margin-top: 10px; background: #1e2530; border-radius: 10px; }
details.code summary { cursor: pointer; padding: 12px 16px; color: #e6ebf2; font-size: 18px; }
details.code pre { margin: 0; padding: 14px 16px; color: #dfe6ef; font-size: 14px; line-height: 1.45; max-height: 380px; overflow: auto; white-space: pre; }
.chips { list-style: none; display: flex; flex-wrap: wrap; gap: 10px; padding: 0; margin: 10px 0 14px; }
.chips li { font-family: Consolas, Menlo, monospace; font-weight: 700; background: var(--soft); border: 2px solid var(--line); border-radius: 30px; padding: 6px 18px; font-size: 20px; }
.donebtn { display: block; width: 100%; margin-top: 22px; background: #fff; color: var(--go); border: 4px solid var(--go); border-radius: 14px; font-size: 26px; font-weight: 800; padding: 16px 20px; cursor: pointer; min-height: 70px; }
.donebtn:hover { background: #EAF5EE; }
.step.s-done .donebtn { margin-top: 12px; background: var(--done); border-color: var(--done); color: #fff; font-size: 20px; min-height: 56px; }
ul.ticks { list-style: none; padding: 0; margin: 12px 0 0; }
ul.ticks li { margin: 10px 0; padding: 12px 14px; background: var(--soft); border-radius: 10px; }
ul.ticks label { display: flex; gap: 14px; align-items: flex-start; cursor: pointer; }
ul.ticks input { width: 30px; height: 30px; flex: 0 0 auto; margin-top: 2px; accent-color: var(--go); }
ul.ticks li.is-done span { text-decoration: line-through; opacity: .6; }
details.ref { margin: 40px 0; background: #fff; border: 2px solid var(--line); border-radius: 16px; padding: 14px 24px; }
details.ref summary { cursor: pointer; font-size: 24px; font-weight: 800; padding: 8px 0; }
table.t { border-collapse: collapse; width: 100%; font-size: 18px; margin: 10px 0 18px; }
table.t th, table.t td { border: 1px solid var(--line); padding: 8px 10px; text-align: left; vertical-align: top; }
table.t th { background: var(--soft); }
.foot { margin: 40px 0 60px; font-size: 18px; color: var(--muted); }
@media (max-width: 640px) { body { font-size: 19px; } .band h1 { font-size: 32px; } .part-name { font-size: 32px; } .title h3 { font-size: 25px; } .num { width: 52px; height: 52px; font-size: 28px; } }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } .bar > i { transition: none; } }
</style>
</head>
<body>
<div class="band">
  <div class="wrap">
    <h1>Branch Contact Groups: update guide</h1>
    <p>Do the steps in order, top to bottom. Tick each one off when it is done.</p>
    <p class="built">This page was built on <strong>@@BUILT@@</strong> (@@VER@@)</p>
    <div class="links"><a href="https://powerapps.pages.dev/">Guide library</a><a href="yaml.html">Screen YAML Vault</a></div>
  </div>
</div>

<div class="sticky" role="region" aria-label="Your progress">
  <div class="wrap">
    <div class="prog">
      <div class="txt" id="progtxt" aria-live="polite">Loading...</div>
      <div class="bar"><i id="progbar"></i></div>
    </div>
    <button class="nextbtn" id="nextbtn" type="button">Go to my next step</button>
  </div>
</div>

<main class="wrap">
  <section class="short">
    <h2>The short answer</h2>
    <p>You need to do <strong>four things</strong> this round, in this order:</p>
    <ul>
      <li><strong>Part 1:</strong> in SharePoint, add <strong>two columns</strong> to the list BM Groups (steps 1 and 2).</li>
      <li><strong>Part 2:</strong> in Studio, refresh BM Groups, then <strong>delete all five screens and paste all five back</strong> (steps 3 and 6 to 11).</li>
      <li><strong>Formulas and OnStart</strong> (steps 4 and 5) have not changed since <strong>@@FDATE@@</strong>, which was @@FDAYS@@ day@@FS@@ ago. If you pasted them on or after that date, skip them.</li>
      <li><strong>Part 3:</strong> test it.</li>
    </ul>
  </section>

  <section class="roadmap">
    <h2>All the steps</h2>
    <p>Click any line to jump to it.</p>
    <ol>@@ROAD@@</ol>
  </section>

  <p><strong>What the coloured pills mean.</strong>
    <span class="pill p-go" style="font-size:18px;padding:4px 14px">GREEN</span> new or changed since you last ticked it, so do it now.
    <span class="pill p-wait" style="font-size:18px;padding:4px 14px">AMBER</span> not ticked yet and it changed a while ago, so do it or tick it if you already have.
    <span class="pill p-done" style="font-size:18px;padding:4px 14px">GREY</span> done. The guide remembers your ticks on this computer and browser.</p>

@@STEPS@@

  <details class="ref">
    <summary>Reference: every SharePoint column (you do not need this to follow the steps)</summary>
    <p>Every column is <strong>Not Required</strong>.</p>
@@LISTS@@
  </details>

  <p class="foot">Built from the real source files. Change times are the real save times of each file, shown in UK time.</p>
</main>

<script>
(function () {
  var K = '@@KEY@@';
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(K) || '{}'); } catch (e) {}
  function persist() { try { localStorage.setItem(K, JSON.stringify(saved)); } catch (e) {} }
  function ukDate(ms) {
    try { return new Date(ms).toLocaleString('en-GB', { timeZone: 'Europe/London', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
    catch (e) { return new Date(ms).toLocaleString('en-GB'); }
  }
  function age(ms) {
    var m = Math.floor(ms / 60000);
    if (m < 1) return 'just now';
    if (m < 120) return m + ' minute' + (m === 1 ? '' : 's') + ' ago';
    var h = Math.floor(m / 60);
    if (h < 48) return h + ' hours ago';
    return Math.floor(h / 24) + ' days ago';
  }
  var steps = Array.from(document.querySelectorAll('article.step'));
  function render() {
    var now = Date.now(), doneCount = 0, firstOpen = null;
    steps.forEach(function (el) {
      var id = el.getAttribute('data-id'), kind = el.getAttribute('data-kind');
      var ch = el.getAttribute('data-changed'), chMs = ch ? new Date(ch).getTime() : 0;
      var doneAt = saved[id] || 0, pill = el.querySelector('[data-pill]'), btn = el.querySelector('[data-done]');
      var ageEl = el.querySelector('.age');
      if (ageEl && chMs) ageEl.textContent = '(' + age(Math.max(0, now - chMs)) + ')';
      var state, text, cls;
      if (doneAt && doneAt >= chMs) { state = 'done'; cls = 'p-done'; text = 'DONE ' + ukDate(doneAt); }
      else if (doneAt && doneAt < chMs) { state = 'go'; cls = 'p-go'; text = 'CHANGED SINCE YOU DID IT. Do it again.'; }
      else if (kind === 'change') {
        var hrs = (now - chMs) / 3600000;
        if (hrs < 72) { state = 'go'; cls = 'p-go'; text = 'NEW. Do this now. Changed ' + age(now - chMs) + '.'; }
        else { state = 'wait'; cls = 'p-wait'; text = 'STILL TO DO. Changed ' + age(now - chMs) + '. Tick it if you already did it.'; }
      }
      else if (kind === 'check') { state = 'wait'; cls = 'p-check'; text = 'QUICK CHECK'; }
      else { state = 'wait'; cls = 'p-late'; text = 'DO THIS AFTER THE STEPS ABOVE'; }
      el.classList.remove('s-go', 's-wait', 's-done'); el.classList.add('s-' + state);
      pill.className = 'pill ' + cls; pill.textContent = text;
      btn.textContent = state === 'done' ? 'Done. Tap here if you want to undo it.' : 'I have done this step';
      if (state === 'done') doneCount++; else if (!firstOpen) firstOpen = el;
    });
    document.getElementById('progtxt').textContent = doneCount + ' of ' + steps.length + ' steps done';
    document.getElementById('progbar').style.width = Math.round(100 * doneCount / steps.length) + '%';
    var nb = document.getElementById('nextbtn');
    nb.textContent = firstOpen ? 'Go to my next step' : 'All done. Well done.';
    nb._target = firstOpen;
  }
  steps.forEach(function (el) {
    el.querySelector('[data-done]').addEventListener('click', function () {
      var id = el.getAttribute('data-id'), ch = el.getAttribute('data-changed'), chMs = ch ? new Date(ch).getTime() : 0;
      if (saved[id] && saved[id] >= chMs) { delete saved[id]; } else { saved[id] = Date.now(); }
      persist(); render();
      var nb = document.getElementById('nextbtn');
      if (saved[id] && nb._target) nb._target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
  document.getElementById('nextbtn').addEventListener('click', function () { if (this._target) this._target.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
  document.querySelectorAll('input[data-tick]').forEach(function (cb) {
    var id = 'tick-' + cb.getAttribute('data-tick'), li = cb.closest('li');
    cb.checked = !!saved[id]; li.classList.toggle('is-done', cb.checked);
    cb.addEventListener('change', function () { if (cb.checked) saved[id] = Date.now(); else delete saved[id]; li.classList.toggle('is-done', cb.checked); persist(); });
  });
  render(); setInterval(render, 30000);

  function flash(btn, msg) { var o = btn.getAttribute('data-label') || btn.textContent; btn.setAttribute('data-label', o); btn.textContent = msg; btn.classList.add('copied'); setTimeout(function () { btn.textContent = o; btn.classList.remove('copied'); }, 2200); }
  function copyText(text, btn, msg) {
    function ok() { flash(btn, msg); }
    function fallback() {
      var ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); ok(); } catch (e) { btn.textContent = 'Copy failed'; }
      document.body.removeChild(ta);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(text).then(ok, fallback); } else { fallback(); }
  }
  document.querySelectorAll('button[data-copy]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var text = document.getElementById(btn.getAttribute('data-copy')).textContent;
      if (btn.getAttribute('data-crlf') === 'true') text = text.replace(/\\r?\\n/g, '\\r\\n');
      copyText(text, btn, 'Copied. Now paste it in Studio.');
    });
  });
  document.querySelectorAll('button[data-text]').forEach(function (btn) {
    btn.addEventListener('click', function () { copyText(btn.getAttribute('data-text'), btn, 'Copied'); });
  });
})();
</script>
</body>
</html>
'''

PAGE = (PAGE
        .replace('@@BUILT@@', uk_text(NOW)).replace('@@VER@@', VERSION).replace('@@KEY@@', KEY)
        .replace('@@FDATE@@', to_uk(T['formulas'])[0].strftime('%d/%m/%Y')).replace('@@FDAYS@@', str(fdays)).replace('@@FS@@', '' if fdays == 1 else 's')
        .replace('@@ROAD@@', road).replace('@@STEPS@@', ''.join(parts_html)).replace('@@LISTS@@', list_tables()))

outs = sys.argv[1:] or [os.path.join(REPO, 'docs', 'index.html')]
for o in outs:
    os.makedirs(os.path.dirname(os.path.abspath(o)), exist_ok=True)
    open(o, 'w', encoding='utf-8', newline='\n').write(PAGE)
    print('wrote', o, len(PAGE), 'bytes')
