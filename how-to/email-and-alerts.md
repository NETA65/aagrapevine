# E-mail and alerts

> **Looking for "the Gmail API code"?** There isn't any. The website sends exactly **one** e-mail by itself,
> the **monthly digest**, and it sends it over plain **SMTP**: the same way a mail program sends mail, with a
> username and an **app password**. The code is [`scripts/notify/send_digest.py`](../scripts/notify/send_digest.py),
> and GitHub starts it from [`.github/workflows/monthly-digest.yml`](../.github/workflows/monthly-digest.yml).
> It stays **switched off** until the NETA65 account adds four secrets (see [Quick start](#2-quick-start-switch-on-the-monthly-e-mail)).
> To change what the e-mail says, see [section 6](#6-going-further-change-the-code). If you really want the
> Gmail API instead, [section 6.6](#66-if-you-want-the-gmail-api-oauth-instead) explains what would have to be added.

**Contents**

1. [What this is](#1-what-this-is)
2. [Quick start: switch on the monthly e-mail](#2-quick-start-switch-on-the-monthly-e-mail)
3. [Full reference](#3-full-reference). Part A covers the monthly digest (3.1 to 3.15). Part B covers the other notifications (3.16 to 3.19).
4. [What happens next](#4-what-happens-next)
5. [Where it shows on the website](#5-where-it-shows-on-the-website)
6. [Going further: change the code](#6-going-further-change-the-code)
7. [Troubleshooting](#7-troubleshooting)
8. [Good practice and AA principles](#8-good-practice-and-aa-principles)
9. [See also](#9-see-also)

---

## 1. What this is

The site can send **one e-mail by itself**: the **monthly digest**. It is a bilingual recap (English first, then
Spanish) of everything that was new on the site **last month**. It goes out once, early each month, to the address
list you choose. The best choice is one Google Group with every DCM, GVR and RLV. The e-mail is the same edition as
the **Monthly digest** page:
[/digest/](https://neta65.github.io/aagrapevine/digest/) and [/es/digest/](https://neta65.github.io/aagrapevine/es/digest/)
(menu **Get involved → Monthly digest**, in Spanish **Participa → Resumen mensual**).

Every other e-mail around the site comes from **GitHub** or from **cron-job.org**, never from the site's code:

| Notification | Sent by | Goes to | How to switch it on |
|---|---|---|---|
| **Monthly digest** (bilingual, HTML + plain text) | `send_digest.py` over SMTP, started by `monthly-digest.yml` | the `DIGEST_TO` secret | NETA65 adds the secrets ([2](#2-quick-start-switch-on-the-monthly-e-mail)) |
| **"Run failed" e-mails** | GitHub | for timed runs, whoever last switched each workflow on or last changed its `cron:` line; for a button press, whoever pressed it | [3.16](#316-githubs-run-failed-e-mails) |
| Issue **"A content source has stopped updating"** | `update.yml`, job *Report sources that stopped updating, and updates that keep failing* | people who **watch** the repository | [3.17](#317-the-three-automatic-issues) |
| Issue **"The website update keeps failing"** | the same job of `update.yml` (since October 2026) | people who watch the repository | [3.17](#317-the-three-automatic-issues) |
| Issue **"Broken links found by the weekly check"** | `link-check.yml` | people who watch the repository | [3.17](#317-the-three-automatic-issues) |
| **Morning alarm failures** | cron-job.org | the cron-job.org account | [3.18](#318-the-morning-alarm-cron-joborg) |

> **State at the time of writing (October 2026):** the digest is **off**, because the secrets it needs are not there
> yet. Every scheduled try ends green with the notice *"E-mail digest is off"*. The September 2026 digest was not e-mailed.
> The failure e-mails of the timed runs still go to the **MKP715** login, and nobody watches the repository yet.
> [Section 2](#2-quick-start-switch-on-the-monthly-e-mail) and [3.16](#316-githubs-run-failed-e-mails) fix all three.

---

## 2. Quick start: switch on the monthly e-mail

This is the usual case: the committee's Gmail account sends the e-mail to one Google Group. Plan about 20 minutes.
Steps 3 and 5 need the **NETA65** GitHub account. The MKP715 login has write access only, and it cannot see or add
secrets.

1. **Make an app password** for the Google account that will send. In that account, turn on **2-Step Verification**.
   Then open <https://myaccount.google.com/apppasswords>, type the name `grapevine digest`, press **Create** and
   copy the 16-letter password. Details are in [3.4](#34-make-a-gmail-app-password-step-by-step).
2. **Get the recipients ready.** Use one Google Group with every DCM, GVR and RLV, and let the sending address post
   to it ([3.6](#36-who-receives-it)).
3. **Add four secrets** while signed in to GitHub as **NETA65**. Go to
   **github.com/NETA65/aagrapevine → Settings → Secrets and variables → Actions → New repository secret** and add
   each one with its name written exactly as shown:

   | Name | Secret |
   |---|---|
   | `SMTP_SERVER` | `smtp.gmail.com` |
   | `SMTP_USERNAME` | the sending account's full address, for example `YOUR-COMMITTEE-ACCOUNT@gmail.com` |
   | `SMTP_PASSWORD` | the 16 letters of the app password, without spaces |
   | `DIGEST_TO` | the group's address, for example `YOUR-GROUP@googlegroups.com` |

4. **Preview it.** Go to **Actions → Monthly e-mail digest → Run workflow** and leave **Preview only** ticked. Press
   **Run workflow**. When the run finishes, open it, find **Artifacts → digest-preview**, unzip it and open
   `digest.html` in a browser ([3.10](#310-preview-it-no-secrets-needed)).
5. **Make the failure e-mails come to NETA65.** Still signed in as NETA65, go to
   **Actions → Monthly e-mail digest → ⋯ (top right) → Disable workflow**, then press **Enable workflow**. Do the same
   for the other three timed workflows ([3.16](#316-githubs-run-failed-e-mails)).
6. **Done.** From now on the e-mail goes out by itself on the **1st** of each month, from **7 AM Central**. If the
   data is not ready, it goes out later, and at the latest from **noon on the 3rd**. To send last month's e-mail
   right away, run the workflow **once** with **Preview only** unticked ([3.12](#312-send-a-month-by-hand)). A month
   is sent only once: pressing it again only says *"Already sent"*, unless you also tick **force**.

**What you will see:** after the next 1st, the run under **Actions → Monthly e-mail digest** has the summary heading
*"E-mail digest sent"*. Below it are the subject (*"Grapevine / La Viña — October 2026 digest · Resumen de octubre de
2026"*) and the line *"Recipients: 1 · new items in October 2026: …"*. The e-mail arrives in the group. Gmail also
keeps a copy in the sending account's **Sent** folder.

---

## 3. Full reference

**Part A covers the monthly e-mail digest (3.1 to 3.15).** Part B covers the other notifications (3.16 to 3.19).

### 3.1 Who can do what

| Task | MKP715 login (write access) | NETA65 account (owner, admin) |
|---|---|---|
| Preview the e-mail (**Run workflow**, *Preview only* ticked) | yes | yes |
| Send a month by hand (*Preview only* unticked; only works once the secrets exist) | yes | yes |
| See, add, change or delete the **secrets** | **no** | yes |
| Edit `send_digest.py`, `monthly-digest.yml` and `config/site.yml` | yes | yes |
| Receive the failure e-mails of the **timed** runs | only while MKP715 was the last to switch the workflows on or change their `cron:` lines (true today) | after **Disable → Enable** as NETA65 ([3.16](#316-githubs-run-failed-e-mails)) |
| Make the morning alarm's key ([3.18](#318-the-morning-alarm-cron-joborg)) | **no** (a fine-grained key only reaches its owner's repositories) | yes |
| **Watch** the repository to get the automatic issues | yes | yes |

### 3.2 The files that make the e-mail

| File | What it does |
|---|---|
| [`.github/workflows/monthly-digest.yml`](../.github/workflows/monthly-digest.yml) | The timer (five tries a day on the 1st to the 3rd), the on/off test, the "send only once" markers and the **Run workflow** form (*Preview only*, *month*, *force*). |
| [`scripts/notify/send_digest.py`](../scripts/notify/send_digest.py) | Builds the e-mail from the site's data files, in HTML and plain text and in both languages, then sends it over SMTP. On GitHub it works in two halves: `--prepare` builds the e-mail and saves it, and `--send-prepared` hands that same e-mail to the server, once. It uses Python's standard library only, so the job needs neither Node.js nor the sync tools. |
| [`config/site.yml`](../config/site.yml) | The `site:` keys (title, committee name, reply address, site address) and the `digest:` keys (rows per list, stories per magazine issue). See [3.8](#38-settings-in-configsiteyml-that-change-the-e-mail). |
| `data/site/*.json` | What goes into the e-mail. The daily update writes these files, so the e-mail never visits Drive or the magazines itself. |
| [`src/pages/digest.njk`](../src/pages/digest.njk) + [`eleventy/filters/community.js`](../eleventy/filters/community.js) (`buildMonthlyDigest`) | The same edition as a web page. Both sides must pick the same items, and a test checks that they do. |
| [`tests/test_send_digest.py`](../tests/test_send_digest.py), [`tests/test_digest_parity.py`](../tests/test_digest_parity.py) | The automatic tests ([6.7](#67-run-the-tests)). |
| Repository **secrets** | The mail server, the login, the password and the recipients. They are never stored in a file. |

You do not need a Google Cloud project, an OAuth screen or a token file for the e-mail. The Google Cloud console in
[README → 10 a](../README.md#a-google-api-key-exact-dates-for-drive-files) is only for the optional `GOOGLE_API_KEY`
(exact Drive dates) and has nothing to do with e-mail.

### 3.3 The secrets

**Where:** go to **github.com/NETA65/aagrapevine → Settings → Secrets and variables → Actions**, open the **Secrets**
tab and press **New repository secret**. Write each name exactly as shown, in capitals with underscores. You can
replace a value with **Update** or remove it with **Delete**, but GitHub never shows it again after saving. Each one
must be a **repository** secret. The workflow does not see a value saved under *Variables*, under an *Environment*
(for example `github-pages`), or under the *Dependabot* or *Codespaces* secrets.

| Secret | Needed? | If empty | Example value | Good to know |
|---|---|---|---|---|
| `SMTP_SERVER` | **yes** | the digest is "off" | `smtp.gmail.com` | Spaces around it are removed. A misspelled host such as `smtp.gmial.com` is tried 3 times, then the run goes red with *"Could not reach the mail server smtp.gmial.com:587: …"*. |
| `SMTP_PORT` | no | `587` | `587` or `465` | `587` means STARTTLS: the server must offer it, or the run stops **before** the password is sent. `465` means an encrypted (SSL) connection from the start. A value that is not a number (for example `STARTTLS`) makes the run go red with *"invalid literal for int() …"*. |
| `SMTP_USERNAME` | **yes** | the digest is "off" | the full mailbox address | When `DIGEST_FROM` is empty and this login contains an "@", it is also the **From** address. |
| `SMTP_PASSWORD` | **yes** | the digest is "off" | the 16 letters of the app password | It is used **exactly as pasted**, without trimming. Paste the 16 letters only, with no space or line break. |
| `DIGEST_TO` | **yes** | the digest is "off" | `YOUR-GROUP@googlegroups.com`, or several addresses | See [3.6](#36-who-receives-it). |
| `DIGEST_FROM` | no | `SMTP_USERNAME` if it contains "@", else `site.contact_email` | an address | Only the address is used. The display name always comes from `site.committee` (else `site.title`). |
| `DIGEST_REPLY_TO` | no | `site.contact_email` (`grapevine@neta65.org`), else the From address | an address | It is also used for the "unsubscribe" header ([3.7](#37-sender-replies-and-unsubscribing)). |

**How the on/off test works:** the first step of every run is *"Is it time, and is the e-mail digest set up?"*. It
checks only the four required secrets. If any of them is empty, the run stops there, green, with the notice
*"E-mail digest is off — Add the SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD and DIGEST_TO secrets to turn it on
(README → Monthly e-mail digest)"* and the summary line *"E-mail digest is not set up — nothing to do. (This is
normal.)"*. A **preview** skips this test, so it works without any secrets.

> Note: the comment at the top of `send_digest.py` says `DIGEST_FROM` defaults to `SMTP_USERNAME`. The code uses
> `SMTP_USERNAME` only when it contains an "@". Otherwise it uses `site.contact_email`. With Gmail the username is
> always a full address, so this makes no difference there.

### 3.4 Make a Gmail app password, step by step

An **app password** is a separate 16-letter password that one program uses to sign in to a Google account. The
digest needs one because it signs in like a mail program. It cannot use the account's normal password. These are
Google's screens, and their wording can change.

1. Sign in at <https://myaccount.google.com> with the account that will **send** the digest. Use a committee
   account, not anyone's personal one ([8](#8-good-practice-and-aa-principles)).
2. Open **Security** (on some screens **Security & sign-in**), then **2-Step Verification**, and turn it on. A phone
   prompt, an authenticator app or a text message all work.
3. Open <https://myaccount.google.com/apppasswords>. You can also type "App passwords" in the account's search box.
4. Type the app name `grapevine digest` and press **Create**.
5. Google shows a 16-letter password, written as four groups of four letters. **Copy it now**, because Google
   shows it only once. Put it in the `SMTP_PASSWORD` secret as **16 letters with no spaces**.
6. Close the window. The NETA65 account then adds the secrets ([Quick start, step 3](#2-quick-start-switch-on-the-monthly-e-mail)).

These rules come from **Google**, not from this site, and Google can change them:

- The **App passwords** page appears only when 2-Step Verification is on. It is not offered to accounts with
  Advanced Protection. A Google Workspace account (such as a neta65.org address) gets it only if its administrator
  allows it.
- **Changing the Google account's own password cancels all of its app passwords.** The next send then goes red with
  *"The mail server rejected the username/password. For Gmail you need an App Password …"* until `SMTP_PASSWORD`
  holds a new app password ([3.15](#315-change-the-password-or-the-recipients-or-stop-the-e-mail)).
- Gmail keeps a copy of each digest in the sending account's **Sent** folder. That copy is the easiest proof that
  the e-mail went out.
- Gmail limits how many recipients one account may send to per day. A Google Group address counts as **one**
  recipient, which is one more reason to use a group.

### 3.5 Send from the neta65.org mailbox or another mail host

The code works with **any** mail provider that offers an encrypted connection. Only the four secrets change.

**neta65.org mail runs on Google** (Google Workspace), according to its public DNS records in October 2026.
Two cases follow from that:

- **`grapevine@neta65.org` is a real mailbox** (a Workspace user that can sign in). Then the settings are the same as
  for Gmail: `SMTP_SERVER` = `smtp.gmail.com`, port `587`, `SMTP_USERNAME` = that neta65.org address, and
  `SMTP_PASSWORD` = an app password made **in that account**. The neta65.org Workspace administrator must allow
  2-Step Verification and app passwords for that user. The e-mail then comes **from** the neta65.org address.
- **`grapevine@neta65.org` is a group or an alias** (it cannot sign in). Ask the administrator for a mailbox that
  can send, such as a dedicated sender address. Otherwise send from the committee's Gmail: replies still go to
  `grapevine@neta65.org`, because that is the default Reply-To.

**Another provider:** ask it for the SMTP **host**, the **port** (587 with STARTTLS, or 465 with SSL), the
**username** and a **password** (some providers call it an "app password" too). Put them in the same secrets.

| Sending mailbox | `SMTP_SERVER` | `SMTP_PORT` | `SMTP_USERNAME` | The e-mail shows From | Replies go to |
|---|---|---|---|---|---|
| Committee Gmail account | `smtp.gmail.com` | *(leave empty: 587)* | `YOUR-COMMITTEE-ACCOUNT@gmail.com` | NETA 65 Grapevine & La Viña Committee &lt;YOUR-COMMITTEE-ACCOUNT@gmail.com&gt; | `grapevine@neta65.org` |
| A neta65.org Workspace mailbox | `smtp.gmail.com` | *(leave empty: 587)* | the neta65.org address | NETA 65 Grapevine & La Viña Committee &lt;that address&gt; | `grapevine@neta65.org` |
| Another host that says "SSL" | the host's name, for example `mail.example.org` | `465` | as the host says | the committee name and that address | `grapevine@neta65.org` |
| Another host that says "TLS" or "STARTTLS" | the host's name | `587` | as the host says | the committee name and that address | `grapevine@neta65.org` |

> Gmail behaviour (not this site's code): if `DIGEST_FROM` is not the signed-in account and not one of its verified
> **"Send mail as"** addresses, Gmail replaces it with the account's own address. Leave `DIGEST_FROM` empty unless
> you have set up such an alias. A From address on a domain the e-mail was not sent through can also be refused by
> that domain's mail policy (DMARC). Stay with port 587 or 465. A server that offers neither STARTTLS nor SSL never
> receives the password, and the run stops with *"The mail server does not offer STARTTLS; refusing to send the
> password unencrypted …"*.

### 3.6 Who receives it

The `DIGEST_TO` secret decides who receives the e-mail. No file in the repository holds the address list.

**The recommended setup is one Google Group** with every DCM, GVR and RLV, and the chair:

- It is one address, so a new or departing district representative is a change in Google Groups. Nothing changes on
  GitHub.
- No district address is ever stored in GitHub.
- Unsubscribing happens in the group ([3.7](#37-sender-replies-and-unsubscribing)).

Settings worth checking in the group (Google Groups behaviour, not this site's code):

- **Who can post:** if only members may post, add the sending address as a member (it can be set to receive no
  e-mail), or allow that address to post. Otherwise the digest is held or bounced.
- **Moderation:** if messages are held for approval, someone must approve the digest each month.
- **Who can see the members** and **who can join:** "managers only" and "invited only" keep the list private.
- A green "sent" run means the mail server **accepted** the e-mail. A group that holds the message, or rejects the
  sender, does so afterwards. That shows in the group's pending messages and in bounce mail to the sending account,
  never in GitHub.

**`DIGEST_TO` examples.** Each result below was checked with the code's own `parse_recipients()` and
`build_message()`:

| `DIGEST_TO` holds | Who receives it | What their **To:** line shows |
|---|---|---|
| `YOUR-GROUP@googlegroups.com` | the group | `YOUR-GROUP@googlegroups.com` |
| `dcm1@example.org, gvr2@example.org; rlv3@example.org` | the three addresses | the committee's own sending address. Nobody sees the other addresses. |
| one address per line | each address | the same as above |
| `Area 65 GVRs <gvrs@example.org>` | `gvrs@example.org` | `gvrs@example.org` (the name part is dropped) |
| `x@example.org, X@example.org, x@example.org` | `x@example.org` and `X@example.org` | Two addresses written exactly alike count once. **A different capitalisation counts as another address**, so that mailbox usually gets two copies. |
| `dcm1@example.org dcm2@example.org` (separated by a space only) | **nobody** | The run goes red. The log says *"e-mail is not configured (missing: DIGEST_TO)"*, and nothing is sent. |
| `not-an-address, , x@y` | `x@y` | Anything containing an "@" is accepted. There is no spelling check. |

Separate addresses with a **comma**, a **semicolon** or a **new line**. A space alone does not separate them.

> Note: the README and the script's top comment say several addresses are "sent as **Bcc**". The code does not
> write a `Bcc:` line: it gives the addresses only to the mail server, and the **To:** line shows the committee's
> own sending address. The effect is the same, and nobody sees the other addresses.

On a computer, `--to` replaces `DIGEST_TO` for a test ([3.11](#311-send-a-test-to-yourself)).

### 3.7 Sender, replies and unsubscribing

These are the real headers of the September 2026 e-mail, as `build_message()` writes them, with placeholder
addresses:

```text
Subject: Grapevine / La Viña — September 2026 digest · Resumen de septiembre de 2026
From: NETA 65 Grapevine & La Viña Committee <YOUR-COMMITTEE-ACCOUNT@gmail.com>
To: YOUR-GROUP@googlegroups.com
Reply-To: grapevine@neta65.org
List-Unsubscribe: <mailto:grapevine@neta65.org?subject=unsubscribe>
Content-Language: en, es
```

The message has two parts, **plain text** and **HTML**. Mail apps show the HTML part. Text-only readers show the
plain-text part.

| Header | Where it comes from | How to change it |
|---|---|---|
| Subject | `site.title` + the edition's name in both languages (`subject_of()`) | `site.title` (this renames the whole site), or the code ([6.5](#65-example-put-neta-65-in-front-of-the-subject)) |
| From (name) | `site.committee`, else `site.title` | `config/site.yml` |
| From (address) | `DIGEST_FROM`, else `SMTP_USERNAME` (if it contains "@"), else `site.contact_email` | secrets |
| Reply-To | `DIGEST_REPLY_TO`, else `site.contact_email`, else the From address | a secret, or `config/site.yml` |
| List-Unsubscribe | the Reply-To address, with the subject "unsubscribe" | follows Reply-To |

**Unsubscribing is done by hand.** The footer says *"To stop receiving it, reply with "unsubscribe"."* (in Spanish,
*"responde con "cancelar""*). The reply goes to the Reply-To address, and the person who reads that mailbox removes
the sender from the group, or from `DIGEST_TO`. Nothing reads these replies automatically. Many mail apps also show
an **Unsubscribe** button based on the `List-Unsubscribe` header. That button sends the same kind of e-mail to the
same address. Google Groups usually adds its own unsubscribe line as well.

### 3.8 Settings in config/site.yml that change the e-mail

| Key | Today | What it changes in the e-mail | Example |
|---|---|---|---|
| `site.title` | `"Grapevine / La Viña"` | The start of the subject, the masthead and the first line of the text part. | Subject: `Grapevine / La Viña — September 2026 digest · Resumen de septiembre de 2026` |
| `site.committee` / `site.committee_es` | `"NETA 65 Grapevine & La Viña Committee"` / `"Comité de Grapevine y La Viña de NETA 65"` | The From name, the line under the masthead, and the footer (*"You are receiving this monthly summary from the NETA 65 Grapevine & La Viña Committee."*). | — |
| `site.contact_email` | `grapevine@neta65.org` | The default Reply-To and unsubscribe address, the mail link in the HTML footer, and the From address when the login has no "@". | — |
| `site.url` | `https://neta65.github.io/aagrapevine` | The address in every link, but only when GitHub Pages cannot be asked (on GitHub the workflow asks Pages first) and when you build on a computer. | If the site moves to its own domain, the e-mail's links follow by themselves. |
| `digest.per_section` | `5` | How many rows each list shows before *"→ and N more on the website"*. | `8` shows 8 rows. `0`, `-1` or `"many"` fall back to 5. |
| `digest.highlights` | `3` | How many stories each magazine issue shows. | `2` |
| `meeting:` (`week_of_month`, `weekday`, `platform`, `skip_dates`) | 3rd Wednesday, `Zoom` | The *"Committee meeting — Wed, Sep 16 · Zoom"* row under "Events in September", which the code works out from this rule when the events data has no record. | `skip_dates: ["2026-12-16"]` removes December's row. |
| `price_changes:` | a change on January 1, 2027 | One extra row after "Coming up", shown while the price notice is on. It is judged on the day the e-mail is **built**. | E-mails built October 1 to December 31 say *"Grapevine and La Viña prices change on January 1, 2027"*. Those built in January say *"New Grapevine and La Viña prices since January 1, 2027"*. From February 1 the row is gone. |

For example, to show fewer stories per issue and more rows per list:

```yaml
digest:
  highlights: 2        # stories shown for each magazine issue
  per_section: 8       # rows per list before "and N more"
```

This changes **both** the e-mail and the [/digest/](https://neta65.github.io/aagrapevine/digest/) page, because they
read the same keys. Saving `config/site.yml` starts a quick **Website update** run, and the page changes within
about 10 to 20 minutes. The e-mail uses the new values the next time it is built, whether that is a preview or a
send. The meaning of every other key is in [Settings](settings.md).

### 3.9 When it goes out: the schedule and its safety rules

**The rules, in order:**

1. **Five tries a day on the 1st to the 3rd.** The schedule is `cron: "7 8,11,14,17,20 1-3 * *"`, which means
   08:07, 11:07, 14:07, 17:07 and 20:07 **UTC**. These times are **set 4 hours early on purpose**: GitHub starts this
   repository's timed runs 4 to 6 hours late, sometimes 8. Do not "fix" the times. A test checks the exact line.
2. **A check in Central time.** A try goes on only on **Central** days 1 to 3, and only from **7 AM Central**.
   Earlier or later it ends with *"Not the time for the monthly digest (Central time: day 2, hour 5) — nothing to
   do."*
3. **Only once a month.** Every send first reads the month's **markers**, small files the runs save as GitHub
   "artifacts", kept 40 days:
   - `digest-sending-YYYY-MM`, saved just **before** the e-mail is handed to the mail server;
   - `digest-sent-YYYY-MM`, saved after the send (also when there was nothing new, and when the e-mail *may* have
     gone out);
   - `digest-unsent-YYYY-MM`, saved when the server took nothing (the next try sends).

   A try that finds a "sent" marker stops: *"The 2026-09 digest was already sent — nothing to do."* A "sending"
   marker whose run left no "unsent" marker after it (the run was cancelled, ran out of time or lost its connection
   between the two, so the e-mail **may** have gone) is never sent again by itself: every try then shows the yellow
   ⚠️ *Digest send not confirmed* with the run's link, and a person decides ([3.12](#312-send-a-month-by-hand)).
   Since October 2026 this holds for a send started by hand too: only the **force** box skips it.
4. **It waits for the month's last items.** Before sending, it checks that every source it reads has been tried
   **after midnight Central on the 1st**. The sources are `announcements`, `manual_events`, `drive`, `articles`,
   `pdfs`, `youtube`, `podcasts` and `instagram`. In practice this means it waits for the month's first **full**
   daily update, which the Morning check starts early on the 1st. Until then each try ends green with *"Digest
   waits"* (exit 3). A source whose last try was more than 3 days before the month ended has stopped, so the e-mail
   does not wait for it.
5. **From noon Central on the 3rd** it stops waiting and sends with the data there is.
6. **Nothing new means no e-mail.** The month still counts as done. Events alone never count as news, so a month
   with only the monthly CityWide booth and the committee meeting sends nothing.
7. **A month cannot be sent before it is over.** A preview of an unfinished month works.

**When the tries actually happen:**

| Try (UTC) | If on time, summer (CDT) | If on time, winter (CST) | Typical start (4 to 6 h late, CDT) |
|---|---|---|---|
| 08:07 | 3:07 AM, skipped (before 7 AM) | 2:07 AM, skipped | 7:07 to 9:07 AM, goes on |
| 11:07 | 6:07 AM, skipped | 5:07 AM, skipped | 10:07 AM to 12:07 PM, goes on |
| 14:07 | 9:07 AM, goes on | 8:07 AM, goes on | 1:07 to 3:07 PM, goes on |
| 17:07 | 12:07 PM, goes on (on the 3rd: "send with the data there is") | 11:07 AM, goes on | 4:07 to 6:07 PM (on the 3rd: send anyway) |
| 20:07 | 3:07 PM, goes on (on the 3rd: send anyway) | 2:07 PM, goes on (on the 3rd: send anyway) | 7:07 to 9:07 PM (on the 3rd: send anyway) |

"Goes on" means the try then checks the marker file and the data. Central time is CDT until November 1, 2026 and CST
after that.

**Example: October 1, 2026, with GitHub 5 hours late.**

1. The 08:07 UTC try starts at about 8:07 AM CDT. It is day 1 and past 7 AM, and there is no marker file yet.
2. The full update, which the Morning check started early, has already tried every source after midnight.
3. So the try saves `digest-sending-2026-09`, sends the **September 2026 digest** and saves `digest-sent-2026-09`.
4. The 11:07 try finds the marker: *"The 2026-09 digest was already sent — nothing to do."*

If YouTube had last been tried at 5:21 PM on September 30, the first try would end with *"Digest waits"*, and a later
try would send the e-mail once YouTube had been read.

> **Note: the ways to send the same month twice.**
> 1. **force** ticked (with *Preview only* unticked) sends again, on purpose. Nothing else does: since October
>    2026 a send by hand checks the markers like a scheduled try (before, it had no guard at all).
> 2. The markers belong to the run that saved them. If someone **deletes that run** during the 1st to the 3rd (while
>    tidying old runs, for example), its markers go with it, and the next try sends again. After the 3rd, deleting
>    old runs is harmless.

> **Note:** GitHub sometimes skips timed runs entirely. With 15 tries in all that rarely matters, but if every try of
> the 1st to the 3rd is skipped or fails, nothing goes out that month by itself. Send it by hand
> ([3.12](#312-send-a-month-by-hand)).

### 3.10 Preview it (no secrets needed)

**On GitHub.** Anyone with write access can do this, including the MKP715 login.

1. Go to **github.com/NETA65/aagrapevine → Actions** and choose **Monthly e-mail digest** in the left list.
2. Press **Run workflow** (on the right) and keep **Use workflow from: main**.
3. Keep **"Preview only — build the e-mail but don't send it (download it from the run's Artifacts)"** ticked. It is
   ticked by default.
4. Fill in **"The month the digest covers, as YYYY-MM"**, or leave it empty for last month.
5. Press the green **Run workflow**. After a minute or two, open the finished run (listed as **"Monthly e-mail
   digest: preview only"**).
6. The summary says *"E-mail digest preview (not sent)"* and shows the subject and the counts. When some data is not
   ready yet, it also says *"A scheduled send would still wait for: …"*.
7. At the bottom of the run page, under **Artifacts**, download **digest-preview**. It is a zip file holding
   `digest.html` (open it in a browser: it looks like the e-mail) and `digest.txt` (the plain-text part). GitHub keeps
   it for 14 days.

| *month* box | Result |
|---|---|
| *(empty)* on October 2 | a preview of the **September 2026** digest |
| `2026-09` | the September 2026 digest |
| ` 2026-09 ` (with spaces around it) | the same, because spaces are removed |
| `2026-10` on October 15 | October so far. A preview of an unfinished month works, but a send does not. |
| `2026-08` | the August 2026 digest (53 items with today's data) |
| `2026-9` or `Oct` | A **red** run: *"Stopped: the month '2026-9' is not a YYYY-MM month like 2026-09. Nothing was sent — run it again with the month written like that, or leave the box empty."* |

If you have the GitHub command-line tool, the same preview is
`gh workflow run monthly-digest.yml -R NETA65/aagrapevine -f preview_only=true -f month=2026-09`.

**On a computer**, in the repository folder (Python 3 is enough, and PyYAML is optional):

```powershell
python -m scripts.notify.send_digest --dry-run                                    # last month → .tmp\digest.html + .tmp\digest.txt
python -m scripts.notify.send_digest --dry-run --month 2026-09 --as-of 2026-10-01 # September, built as on October 1
python -m scripts.notify.send_digest --dry-run --max-per-section 10               # 10 rows per list, this run only
```

The real output on October 2, 2026 was:

```text
[digest] the September 2026 digest (2026-09-01 to 2026-09-30): 153 item(s) {'article': 89, 'episode': 8, 'video': 2, 'post': 46, 'pdf': 1, 'drive': 6, 'announcement': 1} writers=5 · issues=3 events=4
[digest] DRY RUN — subject: Grapevine / La Viña — September 2026 digest · Resumen de septiembre de 2026
[digest] preview written to …\.tmp\digest.html and …\.tmp\digest.txt
```

| Option | What it does |
|---|---|
| `--dry-run` | Builds the e-mail only, and writes `digest.html` + `digest.txt`. It never waits for the data and never sends. |
| `--month 2026-09` | The month the digest covers. Empty means last month (Central time). |
| `--as-of 2026-10-01` | Pretends today is that day (at 15:05 UTC). Use it to see, for example, which price row an e-mail built that day would carry. |
| `--out-dir FOLDER` | Where the preview goes. The default is `.tmp\`, which git ignores. |
| `--max-per-section 10` | Rows per list for this run, instead of `digest.per_section`. |
| `--to you@example.org` | Sends to this address instead of `DIGEST_TO` (sending only). |
| `--stale-ok` | Sends without waiting for the data. |
| `--force` | Sends even when nothing was new, and without waiting. |

The **Code check** builds the same preview on every push of code or settings, in its step *"Check the e-mail digest
still builds"*. A change that breaks the e-mail therefore shows a red ✗ long before the 1st.

### 3.11 Send a test to yourself

**Option A: from a computer.** Nothing is marked on GitHub, so the real send is not affected. This uses PowerShell, in
the repository folder:

```powershell
$env:SMTP_SERVER   = "smtp.gmail.com"
$env:SMTP_USERNAME = "YOUR-COMMITTEE-ACCOUNT@gmail.com"
$env:SMTP_PASSWORD = Read-Host "App password"      # typed at the prompt, so it is not saved in the command history
python -m scripts.notify.send_digest --to you@example.org --month 2026-08 --stale-ok
Remove-Item env:SMTP_PASSWORD
```

It ends with `[digest] sent to 1 recipient(s): Grapevine / La Viña — August 2026 digest · Resumen de agosto de 2026`.
`--to` replaces `DIGEST_TO`, and `--stale-ok` sends without waiting for the data. A month that is not over yet is
refused.

**Option B: through GitHub.** This needs the NETA65 account.

1. Temporarily set the `DIGEST_TO` secret to **your own** address.
2. Run the workflow with *Preview only* unticked and an **old** month in the month box, for example `2026-08`. Only
   that old month is then marked as sent (`digest-sent-2026-08`). If that month was sent before, tick **force** too,
   or it only says *"Already sent"*.
3. **Put the real `DIGEST_TO` back** before the 1st.

Never test this way with last month during the 1st to the 3rd: the test would mark that month as sent, and the
districts would never get it.

### 3.12 Send a month by hand

To send by hand, go to **Actions → Monthly e-mail digest → Run workflow** and **untick Preview only**. Leave the month
box empty for last month, or type `YYYY-MM`. Then press **Run workflow**. The run is listed as **"Monthly e-mail
digest: SEND NOW (started by hand)"**, so a send is easy to tell from a preview in the Actions list.

What a manual send does:

- It sends **at once, with the data there is**, without waiting for the update.
- It skips the day and hour checks, but **not the markers** (since October 2026): a month already sent is not sent
  again (a yellow ⚠️ *Already sent*: *"The 2026-09 digest was already sent, so nothing was sent now. To send it a
  second time, run this workflow again with "force" ticked."*), and a month whose send was not confirmed is not
  sent either (⚠️ *Digest send not confirmed*).
- Like every send, it saves the "sending" marker first and the "sent" marker afterwards, so the scheduled tries
  skip that month.
- When nothing was new that month, it sends nothing but still marks the month.

**Send a month again (force).** Tick **force** as well as unticking *Preview only*. The run is listed as **"Monthly
e-mail digest: SEND AGAIN (forced, started by hand)"** and skips the marker check: every district gets the e-mail a
second time, so check the group first. With *Preview only* **and** *force* ticked, it is only a preview.

| Situation | What to do |
|---|---|
| The secrets were added on the 1st, 2nd or 3rd | Nothing, as long as a try is still to come: a later scheduled try sends last month's digest. If they were added on the 3rd after its last try (usually in the evening), run it by hand. |
| The secrets were added later, for example on October 10 | Run it by hand with the month box empty, and September goes out now. October then goes out by itself on November 1 to 3. |
| GitHub skipped every try of the 1st to the 3rd | Run it by hand with the month box empty. |
| A run went red with *"The digest MAY have been sent"* | **First** check the group and the sending account's Sent folder. Only if the e-mail is not there, send it by hand with **force** ticked (the month is marked as sent). |
| Every try shows ⚠️ *Digest send not confirmed* | A send broke off between the "sending" and the "sent" marker. Check the group. If the e-mail arrived, nothing needs doing (the yellow note is harmless, GitHub e-mails nobody about it, and it stops after the 3rd). If it did not, send it with **force**. |
| A resend after a mistake | Tick **force**. A resend goes to **everyone** again, so only do it if really needed. |
| You want this month's digest early | It cannot be sent: *"Not sent: October 2026 is not over yet — its digest can be sent from 2026-11-01. For a look at it now, run it with Preview only ticked."* |

With the GitHub command-line tool, a manual send is
`gh workflow run monthly-digest.yml -R NETA65/aagrapevine -f preview_only=false -f month=2026-09` (add
`-f force=true` to send it again).

### 3.13 What is in the e-mail

Each language half has the same sections, in this order. The English half comes first, then the Spanish one, where
La Viña comes first. A section with nothing in it is left out.

| # | Section | Comes from | Counted in the month when… | Guide |
|---|---|---|---|---|
| 1 | Headline + one sentence (*"In September: 89 magazine stories, 8 podcast episodes, …"*) | the counts below | — | — |
| 2 | **Bulletin** (pinned posts first; a long post is cut, followed by "Details →") | Drive `bulletin` folder, `content/bulletin/*.md` | …it was **added** to the site, never before its `publish:` day. A post is left out if it expired before the day the e-mail is built. | [Bulletin](bulletin.md) |
| 3 | **Events in September**: days only, place and link, including the committee meeting | dated flyers, `content/events/*.md`, `recurring_events:`, outside calendars, `meeting:` | …the event **starts**. Events alone never send an e-mail. | [Flyers and events](flyers-and-events.md) |
| 4 | **Committee uploads**, with pills such as [Reports], [Notes], [Slides], [Flyers], [Workshops], [Forms] and [Files]. Photos get **one row per album**. | Drive panel folders (never the booth folder: its files are only on the booth display) | …the later of the date in its name and the day the site first had it | [Photos, slides and reports](photos-slides-reports.md), [Drive panel folder](drive-panel-folder.md) |
| 5 | **New in the magazines**: per issue, its theme, story count, 3 highlights and "See all N stories" | the magazines' websites | …its stories came out online | [Automatic sources](automatic-sources.md) |
| 6 | **Writers from Area 65 & Texas** | the published-writers data | …the story came out | [Automatic sources](automatic-sources.md) |
| 7 | **Podcasts** (a YouTube copy of an episode shows as "also on YouTube"), **Videos**, **Instagram** (per account: the count and the 3 newest posts; the text part gives counts only), **Documents** | podcasts, YouTube, Instagram, the document library | …the item's date | [Automatic sources](automatic-sources.md) |
| 8 | **Coming up in October**: ONE link to `/monthly/2026-10/`, plus the price-change row while that notice is on | the toolkit page, `price_changes:` | — | [Settings](settings.md) |
| 9 | The buttons **Everything new** and **Open the website**, plus *"Some titles were translated automatically."* when that is true | — | — | [Translations](translations.md) |

Then comes the **footer**:

- why the reader gets the e-mail and how to unsubscribe;
- in the HTML part, *"Feel free to forward it to your group or district — and please protect everyone's anonymity."*;
- the AA Grapevine and A.A.W.S. reprint notice in both languages;
- the site's address.

**Never added by the e-mail itself, on purpose:** the meeting's Zoom link, passcode or phone numbers, event times,
"every month", "to be confirmed", a Book of the Month section (the "Coming up" sentence only names it), subscription
prices and the daily quote. The test `test_nothing_of_what_is_current` fails if, for example, a `zoom.us` or `tel:`
link, "7:00 PM", "every month", "to be confirmed", a "BOOK OF THE MONTH" heading or "daily quote" slips in. All of
this belongs to the monthly toolkit page, which the e-mail links to. A bulletin post's own text, however,
is copied as written. Keep such details out of any post you do not want e-mailed.

**The real September 2026 edition** (text part, start, abridged, with Drive links shortened):

```text
Grapevine / La Viña — Monthly digest · Resumen mensual
NETA 65 Grapevine & La Viña Committee
English first · Versión en español más abajo

=====================
September 2026 digest
=====================
Everything new on the site in September

In September: 89 magazine stories, 8 podcast episodes, 2 videos, 46 Instagram posts, 1 document, 6 committee files and 1 bulletin post.

BULLETIN (1)
------------
* Grapevine and La Viña — ways to carry the message
  A living list of simple ways members, groups and districts can support Grapevine and La Viña …
  Details: https://drive.google.com/file/d/…/view
  → https://neta65.github.io/aagrapevine/bulletin/

EVENTS IN SEPTEMBER
-------------------
* GV/LV booth at CityWide Dallas — Sat, Sep 12 · Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220
  https://citywidedallasaa.org
* Committee meeting — Wed, Sep 16 · Zoom
  https://neta65.github.io/aagrapevine/meetings/
…

COMMITTEE UPLOADS (6)
---------------------
* [Reports] Grapevine Area Chair Meeting Report (May 12)
  https://drive.google.com/file/d/…/view
  …
  → and 1 more on the website: https://neta65.github.io/aagrapevine/portfolio/

…

COMING UP IN OCTOBER
--------------------
The committee meeting, events and story deadlines, this month's magazine issues and the Book of the Month. https://neta65.github.io/aagrapevine/monthly/2026-10/
Grapevine and La Viña prices change on January 1, 2027: https://neta65.github.io/aagrapevine/shop/#price-changes

Everything new: https://neta65.github.io/aagrapevine/whats-new/
Some titles were translated automatically.
```

Left out above (the "…" lines): two more events, four more uploads, and the sections *New in the magazines*,
*Writers from Area 65 & Texas*, *Podcasts*, *Videos*, *Instagram* and *Documents*. The report row shows *(May 12)*,
the date in its file name, but it is in the **September** edition because the site first had it on September 25.
The Spanish half repeats everything in Spanish (*"BOLETÍN (1)"*, *"Reunión del comité — mié, 16 de sept · Zoom"*),
with links to `/es/` pages.

The **HTML part** is a 600-pixel card. It has a dark-blue masthead with the committee logo and the line *"Grapevine /
La Viña · Monthly digest"*, then a strip saying *"English first · Versión en español más abajo"*. Each section has a
coloured heading, and the magazine covers are sent as JPEG pictures, because older Outlook versions cannot show WebP.
Pictures load from the live site.

### 3.14 Every result a digest run can show

Each run's title in the Actions list says what it is, from the same input as the run itself: **"Monthly e-mail digest
(GitHub schedule)"** for a scheduled try, **"Monthly e-mail digest: preview only"** for a preview, **"Monthly
e-mail digest: SEND NOW (started by hand)"** for a send by hand, and **"Monthly e-mail digest: SEND AGAIN (forced,
started by hand)"** for a send with **force** ticked.

The message appears on the run page (**Actions → Monthly e-mail digest → the run**): in the summary, as a notice (ℹ️),
a warning (⚠️) or an error (❌), and in the log of the step that wrote it. The rows down to *"Digest send not
confirmed"* come from the step *"Is it time, and is the e-mail digest set up?"*. Since October 2026 the rest comes
from *"Build the digest (and decide whether to send it)"* (`send_digest --prepare` or `--dry-run`: previews,
"nothing new", "waits", the month and data checks) and, for a real send, from *"Send the digest"*
(`send_digest --send-prepared`: everything about the mail server). Between the two, *"Mark the month as being sent"*
saves the "sending" marker; after them, *"Mark the month as sent"* or *"Mark this try as not sent"*. The run's own job
is *"Build & send the digest"*. The e-mail digest **never** shows on the
[/status/](https://neta65.github.io/aagrapevine/status/) page.

| What the run says | Exit code | Colour | Month marked as sent? | Next scheduled try | What to do |
|---|---|---|---|---|---|
| ℹ️ *"E-mail digest is off"* + *"E-mail digest is not set up — nothing to do. (This is normal.)"* | — (first step) | green | no | the same again | Add the four secrets (NETA65). |
| *"Not the time for the monthly digest (Central time: day N, hour N) — nothing to do."* | — | green | — | — | Nothing. |
| *"The 2026-09 digest was already sent — nothing to do."* | — | green | yes (earlier) | skips | Nothing. |
| ⚠️ *"Digest not sent yet: Could not check whether the 2026-09 digest was already sent (the GitHub API did not answer) — nothing was sent; the next try checks again."* | — | green | no | checks again | Nothing (a GitHub hiccup). |
| ⚠️ *"Already sent: The 2026-09 digest was already sent, so nothing was sent now. To send it a second time, run this workflow again with "force" ticked."* (a send by hand) | — | green | yes (earlier) | skips | Nothing, or tick **force** to send it again ([3.12](#312-send-a-month-by-hand)). |
| ⚠️ *"Digest send not confirmed: A send of the 2026-09 digest was started (…run link…) but never confirmed — the e-mail MAY have gone out. Nothing is sent again by itself: check the group (or the mailbox); if it did not arrive, run this workflow with Preview only unticked and "force" ticked."* | — | green | — (a "sending" marker) | the same note | Check the group; send with **force** only if it did not arrive. |
| *"E-mail digest preview (not sent)"* | 0 | green | no | — | Download **digest-preview**. |
| *"E-mail digest sent"*, then the subject and *"Recipients: 1 · new items in September 2026: 153 …"* | 0 | green | **yes** | skips | Check that the group received it. |
| The same, plus in the log only *"WARNING: 1 recipient(s) were refused by the mail server"* (several addresses in `DIGEST_TO`, and the server refused some of them) | 0 | green | **yes** | skips | The others got it. Fix the refused address in `DIGEST_TO`. |
| *"Nothing new in September 2026 — no e-mail sent."* | 0 | green | **yes** | skips | Nothing. |
| ℹ️ *"Digest waits"* + *"E-mail digest: waiting for the data — Waiting for youtube, … to be updated since September 2026 ended …"* | 3 | green | no | sends once the data is fresh, or anyway from noon on the 3rd | Nothing. |
| ❌ *"The digest was not sent: The mail server took nothing (see the log above) — the next try sends it."*, with one of the five *"Sending FAILED: …"* lines below in the log of *"Send the digest"* | 1 | **red** | no ("unsent") | tries again | As below. |
| *"Sending FAILED: The mail server rejected the username/password. For Gmail you need an App Password …"* | 1 | **red** | no | tries again | Make a new app password and update `SMTP_PASSWORD`. |
| *"Sending FAILED: Could not reach the mail server smtp.gmial.com:587: …"* (after 3 tries, 10 and 20 seconds apart) | 1 | **red** | no | tries again | Fix `SMTP_SERVER` or `SMTP_PORT`. |
| *"Sending FAILED: The mail server does not offer STARTTLS; refusing to send the password unencrypted …"* | 1 | **red** | no | fails again | Use port 587 (STARTTLS) or 465 (SSL). |
| *"Sending FAILED: All recipients were refused: [ … ]"* | 1 | **red** | no | tries again | Fix `DIGEST_TO`, or the group's settings. |
| *"Sending FAILED: The mail server refused the e-mail (…); it was not sent."* | 1 | **red** | no | tries again | Check the sender address and the provider's limits. |
| *"Sending FAILED: invalid literal for int() …"* | 1 | **red** | no | fails again | Make `SMTP_PORT` a number, or delete it. |
| Log only: *"e-mail is not configured (missing: DIGEST_TO) …"* | 2 | **red** | no | the same again | Separate the addresses with commas ([3.6](#36-who-receives-it)). |
| *"Stopped: the month '2026-9' is not a YYYY-MM month like 2026-09 …"* | 2 | **red** | no | — | Type the month as `2026-09`, or leave the box empty. |
| *"Not sent: October 2026 is not over yet — its digest can be sent from 2026-11-01 …"* | 2 | **red** | no | — | Preview it instead, or wait. |
| ❌ *"The digest MAY have been sent: The connection broke while the e-mail was being handed over. The month is marked as done so no later try sends it again. Check the group; if it did not arrive, send it with Run workflow (Preview only unticked, force ticked)."* + *"Sending FAILED — it MAY have been sent: …"* | 4 | **red** | **yes** | skips | Check the group and the Sent folder. Send with **force** only if it is missing. |

Why exit 4 exists: connecting and logging in are tried up to 3 times, but the message itself is handed to the server
**once**. If the line breaks at that moment, the server may already have the e-mail, and another try could send the
whole district list a second copy. So the run marks the month as done and goes red, and a person checks.

A **red** run sends GitHub's failure e-mail ([3.16](#316-githubs-run-failed-e-mails)). For a scheduled try it goes to
whoever last switched the workflow on; for a manual run, to whoever pressed the button.

> Note: the "not configured" result (exit 2, `DIGEST_TO` without a valid address) writes nothing to the run summary.
> Open the log of *"Build the digest (and decide whether to send it)"* to read it.

The exit codes of `--send-prepared` (the step *"Send the digest"*): **0** sent, **4** it may have been sent, **1**
not sent (the server took nothing), **2** the mail settings are missing. A run stopped between *"Mark the month as
being sent"* and the marker after the send (cancelled, out of time) leaves only the "sending" marker: the next tries
then say *"Digest send not confirmed"* (above).

### 3.15 Change the password or the recipients, or stop the e-mail

Every change to a **secret** needs the **NETA65** account. Group members are changed in Google Groups.

- **New app password** (do it yearly, or when people change):
  1. Create a new app password ([3.4](#34-make-a-gmail-app-password-step-by-step)).
  2. On GitHub go to **Settings → Secrets and variables → Actions**, press **`SMTP_PASSWORD` → Update secret**, paste
     it and press **Update secret**.
  3. In Google, delete the old app password at <https://myaccount.google.com/apppasswords>.
- **After the Google account's password changed:** all of its app passwords stopped working. Do the three steps
  above.
- **Change who receives it:** edit the Google Group's members, with no change on GitHub. Or update `DIGEST_TO`.
- **Send from another account:** update `SMTP_USERNAME` and `SMTP_PASSWORD`. For another provider, also update
  `SMTP_SERVER`, and `SMTP_PORT` if it is not 587.
- **Pause or stop the digest:** delete the `SMTP_PASSWORD` secret. Every try then ends green with *"E-mail digest is
  off"*. Alternatively, go to **Actions → Monthly e-mail digest → ⋯ → Disable workflow**, and no try runs at all.
  Whoever switches it back on later receives its failure e-mails.
- **New chair:** the secrets stay with the repository. If the sending account changes, its new owner makes a new app
  password. The person who should receive the failure e-mails does the **Disable → Enable** step
  ([3.16](#316-githubs-run-failed-e-mails)).

---

**Part B covers the other notifications.**

### 3.16 GitHub's "run failed" e-mails

GitHub, not the site, e-mails a person when a workflow run fails (a red ✗). Who receives that e-mail depends on what
started the run:

| The run was started by… | GitHub e-mails… |
|---|---|
| a **timed schedule** (a `cron:` line) | the person who last **switched the workflow on**, or a person who changed its `cron:` line after that |
| the **Run workflow** button | whoever pressed it |
| a **push** (saving a file) | whoever pushed |
| the **morning alarm** (cron-job.org) | the owner of the alarm's key ([3.18](#318-the-morning-alarm-cron-joborg)) |
| the site itself (the Morning check's refreshes, the bot) | **nobody**. That is why the Morning check fails *itself* when a morning goes wrong, and why the issue *"The website update keeps failing"* exists ([3.17](#317-the-three-automatic-issues)). |

The four **timed** workflows are **Website update**, **Morning check (new day by 5:30 AM)** (its hourly
backstop), **Monthly e-mail digest** and **Weekly link check**. Their schedules were last pushed from the MKP715
login, so their failure e-mails go to **MKP715** until the step below is done.

**The owner step**, done once while signed in as **NETA65**:

1. Click your picture → **Settings → Notifications**. Under **System → Actions**, tick **Email** and **Only notify
   for failed workflows**.
2. Go to **github.com/NETA65/aagrapevine → Actions → Website update → ⋯** (top right) **→ Disable workflow**. Then
   press **Enable workflow** in the banner or in the same menu.
3. Do the same for **Morning check (new day by 5:30 AM)**, **Monthly e-mail digest** and **Weekly link check**.
4. Repeat steps 2 and 3 whenever someone else changes a workflow's `cron:` line, and when a new chair takes over.

> Never add an automatic "enable workflow" keep-alive through the GitHub API. The failure e-mails would then go to
> the bot, which means to nobody.

What you would be e-mailed about (details in [Automation and troubleshooting](automation-and-troubleshooting.md)):

| Workflow | Goes red when… | The live site meanwhile |
|---|---|---|
| Website update | building the site data failed, the data commit could not be saved, a change of the code failed the tests (*"Tests failed — not published"*), or the build or deploy failed | keeps the last good version || Morning check (new day by 5:30 AM) | today's update did not reach the site: *"❌ Today's update did not reach the site."* plus the error *"Morning update failed"* | keeps yesterday's day and quote |
| Monthly e-mail digest | a send failed, the month box was mistyped, or the e-mail *may* have been sent ([3.14](#314-every-result-a-digest-run-can-show)) | unaffected |
| Weekly link check | only when the site itself fails to build for the check. Broken links never turn it red: it reports them through an issue. | unaffected |
| Code check (tests and test build), after a push | a change broke the tests, the test build (a build warning too) or a browser check — also a slip in a settings or content file, which *Website update* publishes without the part it could not read. GitHub e-mails the person who pushed. | unaffected (or published without that part) |

A **yellow ⚠** note, for example one source having a bad day, never sends an e-mail. Only red runs do.

### 3.17 The three automatic issues

Two workflows keep three GitHub issues, one of each title. GitHub e-mails new issues and new comments to everyone who
**watches** the repository.

| Issue title (exact) | Opened by | When | While it is open | It closes |
|---|---|---|---|---|
| **A content source has stopped updating** | Website update, job *"Report sources that stopped updating, and updates that keep failing"* | a source has failed, with no success for **7 days or more** (or never worked), or no run has even tried a working source for 7 days ("not checked"). The optional outside calendars never count. | Its text is updated silently after every run. A **comment**, which means an e-mail, is added only when a **new** source starts failing. | by itself: *"Every content source is updating again (…). Closing automatically."* |
| **The website update keeps failing** (since October 2026) | the same job, its second step | a Website update run that **nobody started by hand** (GitHub's schedule, or the Morning check) fails right after another failed run. A run a person started never opens it: GitHub e-mails that person. | *"The website update has failed N times in a row"*, updated silently after each failure; a **comment** only when another job starts failing (*"Now also failing: …"*). It names the failing job and what to do. | by itself, after the next run in which every job worked: *"The website update works again: this run published the site (…). Closing automatically."* |
| **Broken links found by the weekly check** | Weekly link check, on Sundays (cron `40 8 * * 0` = 08:40 UTC, 4 hours early on purpose) | the check finds a broken link, or a link in `config/site.yml` no longer answers | a **new comment every Sunday** while problems remain | by itself: *"All links look good now (…). Closing automatically."* |

This is what the first issue looks like, as the code writes it (example values):

```text
1 content source(s) of the website have not updated for 7 days or more. The website still works and keeps showing
their older items, but nothing new arrives from them until the cause is fixed.

| Source                           | Last successful update | Problem reported |
| Google Drive (committee uploads) | 2026-11-02 (8 days ago) | `…the error message…` |

What to do
- Google Drive (committee uploads): check that the committee folder (config/site.yml → drive → root_folder_id) is
  still shared as Anyone with the link — Viewer (README → section 2).

Status page · Latest run · Troubleshooting

This issue is updated after every Website update run and closes by itself once every source works again.
```

The second issue exists because nobody gets GitHub's failure e-mail for the robot's runs, and a timed run's reaches
only whoever last switched the workflow on ([3.16](#316-githubs-run-failed-e-mails)): two failures in a row of the
nightly update or the morning refresh could otherwise go unseen. Details:
[Automation and troubleshooting §8.4](automation-and-troubleshooting.md#84-the-website-update-keeps-failing).

**Get these e-mails.** Both accounts can do this:

1. Open the repository page and press **Watch** (top right). Choose **All Activity**, or **Custom** with **Issues**
   ticked, and press **Apply**.
2. Under **Settings → Notifications → Subscriptions → Watching**, make sure **Email** is ticked.

Until someone watches the repository, these issues e-mail nobody. They still show in the **Issues** tab.

The advice depends on the source. Besides the Google Drive line above: Instagram's (add the token, or list posts by
hand); the **Texas writers archive**'s: "check the newest file in content/archive: it must keep the archive's
columns, and a file much smaller than the one used before is not used (the run summary's "CSV file to fix" line says
which). The archive already on the site stays meanwhile." ([Writers archive](writers-archive.md)); a source **not
checked** for 7 days: "no run has got to it for N days: the update stops before it (open the latest "Nightly full
update" run and look for the step that failed or ran out of time), or no longer runs it."; any other source: "the
other website may have changed or be down. Send this issue to whoever helps with the website."

**Change them.** In [`update.yml`](../.github/workflows/update.yml), the report job holds the title (`TITLE = "A
content source has stopped updating"`), the advice for each source (`HINTS`, which today covers `drive`,
`instagram` and `writers_archive`) and the "not checked" advice (`UNCHECKED`); its second step holds the other
issue's title (`TITLE = "The website update keeps failing"`) and its advice per job (`HINTS`). The 7 days are `STALE_DAYS = 7`, in
the sync job's *"Write run summary"* step. That step also writes the
run summary's line *"Not updating for 7+ days"*, so change the README's promise too. In
[`link-check.yml`](../.github/workflows/link-check.yml) the title is `ISSUE_TITLE`. The bot finds its open issue by
the **exact** title, so after a title change it opens a new issue and leaves the old one open: close the old one by
hand.

### 3.18 The morning alarm (cron-job.org)

GitHub starts the site's timed runs hours late. The **morning alarm** is a free outside alarm clock at
[cron-job.org](https://cron-job.org). At **4:30 AM Central** every day it presses the **Morning check** button
through GitHub's API. The check then puts the new day and both daily quotes on the site by the goal in
`site.morning_goal`, which is 5:30 AM. The alarm runs **on time**. The "4 hours early" rule is only for GitHub's own
`cron:` lines, so leave the alarm at 4:30. In the Actions list its runs are titled **"Morning check (started by
…)"** with the login that owns the key (NETA65, when NETA65 made it); the hourly backstop's runs are "Morning check
(GitHub schedule)".

**Who is told what:**

| Event | Who is told |
|---|---|
| The alarm's call to GitHub fails, or works again after failing | cron-job.org e-mails **its own account**, as long as the job's notifications "execution fails" and "succeeds after previously failing" are ticked |
| A Morning check **started by the alarm** goes red | GitHub e-mails the **owner of the alarm's key** (NETA65, when NETA65 made the key) |
| A Morning check started by the hourly backstop goes red | GitHub e-mails whoever last switched **Morning check (new day by 5:30 AM)** on, or last changed its `cron:` line ([3.16](#316-githubs-run-failed-e-mails)) |
| Only a magazine's quote was late | nobody: the run stays green with a yellow note *"A daily quote is late at the source"* |

**When cron-job.org e-mails a failure**, open the job's **History** to see GitHub's answer:

| Answer | Meaning | Fix |
|---|---|---|
| **401** | The key expired or was deleted. | Make a new key and replace the value after `Bearer ` in the job's *Authorization* header. |
| **403** | The key's **Actions** permission is not *Read and write*. | Edit the key's permissions. |
| **404** | The repository or the workflow file was renamed, the URL is wrong, or the key cannot see the repository. A job still using the old `…/repos/MKP715/AAGrapevine/…` address gets 404. | Fix the URL to `https://api.github.com/repos/NETA65/aagrapevine/actions/workflows/morning.yml/dispatches`, and check the key's repository access. |
| **422** | The request body is not exactly `{"ref":"main"}`, or the Morning check is switched off. | Fix the body, or go to **Actions → Morning check (new day by 5:30 AM) → Enable workflow**. |

While the alarm is broken the site still updates, just later in the day.

**Set it up once, as NETA65.**

1. Make a fine-grained key. Go to **Settings → Developer settings → Personal access tokens → Fine-grained tokens**
   and choose: resource owner **NETA65**, repository **aagrapevine** only, **Actions: Read and write**, and an expiry
   one year ahead.
2. At cron-job.org, create a job that sends a `POST` to the URL above at 4:30 in the `America/Chicago` time zone,
   with the body `{"ref":"main"}`.
3. Press **Test run**. The answer must be **204**.

The full click-by-click steps, with every header, are in
[README → 10 d](../README.md#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended). The MKP715 login
cannot make this key, because a key only reaches its own account's repositories.

**Every year:** renew the key about a week before it expires (**Regenerate token**), paste the new key at
cron-job.org, press **Test run** and write the new date in a calendar.

**If the key leaks** (someone could see it):

1. Delete the key at once.
2. Check **Actions** for a workflow someone switched off.
3. Make a new key.

The key can do anything the Actions tab can do, including sending the monthly e-mail to every district again. Never
paste it into a repository file, an issue or an e-mail.

**See that it works:** each morning, **Actions → Morning check (new day by 5:30 AM)** has a run that says
*"✅ Today's update is on the site since 4:34 AM CDT — goal 5:30 AM."*. The **Daily quote** row on
[/status/](https://neta65.github.io/aagrapevine/status/) says when the quotes came in.

### 3.19 What is never e-mailed

- **Notes on green runs**, whether a blue ℹ️ notice (*"Digest waits"*, *"E-mail digest is off"*) or a yellow ⚠️
  warning (one source failing for a day, a late daily quote).
- The **run summaries** and the [/status/](https://neta65.github.io/aagrapevine/status/) page
  ([/es/status/](https://neta65.github.io/aagrapevine/es/status/)). You have to look at them.
- Runs that the site starts for itself, which are the bot's runs.
- **Nothing in the site's pages sends e-mail.** The "Write to the chair" link opens the **visitor's** own mail
  program. "Copy for e-mail" copies the digest's text so the visitor can paste it ([5](#5-where-it-shows-on-the-website)).

---

## 4. What happens next

| You do… | What runs | When it takes effect |
|---|---|---|
| Add or update a **secret** (NETA65) | nothing at once | at the next digest run: a scheduled try on the 1st to the 3rd, or **Run workflow** |
| **Run workflow** with *Preview only* ticked | Monthly e-mail digest, preview | about 1 to 2 minutes, then **digest-preview** is on the run page |
| **Run workflow** with *Preview only* unticked | Monthly e-mail digest, sends at once (unless that month was already sent: then tick **force** too) | about 1 to 2 minutes for the run, plus a few minutes for the group to deliver it |
| Nothing (the 1st of the month) | the scheduled tries | usually the **morning of the 1st** (Central), once the month's first full update has run; at the latest from noon on the 3rd |
| Edit `digest:` or `site:` in `config/site.yml` | a quick **Website update** and a **Code check** (started by the push; it tests the change) | [/digest/](https://neta65.github.io/aagrapevine/digest/) in about 3 minutes, up to 13 before every visitor sees it; the e-mail the next time it is built |
| Edit `scripts/notify/send_digest.py` | a **Code check** (all tests plus a preview build) and a quick Website update | the next preview or send uses it straight away |
| Edit `.github/workflows/monthly-digest.yml` | a **Code check** only | the next run. **If you changed the `cron:` line, the failure e-mails now come to you**, so the NETA65 Disable → Enable step must be done again. |
| Add content (Drive, bulletin, events) during the month | the daily updates | in **next month's** e-mail; on [/whats-new/](https://neta65.github.io/aagrapevine/whats-new/) right after the next update |
| Save a `how-to/*.md` file | nothing | — |

The e-mail reads the data files that are on `main` **when it runs**, and it waits for the first full update after
the month ends. So an item that carries **its own date** still gets into that month's e-mail, for example a podcast
episode out at 11:15 PM on the 30th, a video or a magazine story. A **committee upload** or a **bulletin post** is
different: it counts on the day the **site first had it**. The timed updates read Drive only overnight and in the
morning, so a file dropped into the Drive folder on the last day of the month, after that morning's updates, is first
seen after midnight and lands in the **next** month's edition. To have it in this month's e-mail, run **Website update**
by hand after adding it (tick *skip_crawl* for a run of a few minutes), before midnight Central
([Automation and troubleshooting](automation-and-troubleshooting.md)). Every timed schedule in this repository is set
4 hours early on purpose ([3.9](#39-when-it-goes-out-the-schedule-and-its-safety-rules)).

---

## 5. Where it shows on the website

| Where | What you see |
|---|---|
| **The recipients' inboxes** | The e-mail: English first, then Spanish. |
| [/digest/](https://neta65.github.io/aagrapevine/digest/) and [/es/digest/](https://neta65.github.io/aagrapevine/es/digest/) (menu **Get involved → Monthly digest**) | **The same edition** as a web page. It appears with the first build on the 1st and stays all month, so September's digest is shown all through October. The page has **Copy for WhatsApp**, **Copy for e-mail** and **Print / save a copy** buttons. Its card *"Get it by e-mail — Ask the chair to send it each month"* (on small screens, *"Prefer e-mail? … Write to the chair"*) opens a mail to `meeting.chair_email` (else `site.contact_email`) with the subject *"Please send me the monthly Grapevine / La Viña digest"* (in Spanish, *"Por favor envíenme el resumen mensual de Grapevine / La Viña"*). |
| [/whats-new/](https://neta65.github.io/aagrapevine/whats-new/) and [/es/whats-new/](https://neta65.github.io/aagrapevine/es/whats-new/) | A *"Prefer e-mail?"* box with the same *"Write to the chair"* link. |
| The home page's daily quote ([/](https://neta65.github.io/aagrapevine/) and [/es/](https://neta65.github.io/aagrapevine/es/)) | A *"Get it by e-mail"* link (*"Recíbela por correo"*) to the magazine's **own** daily-quote sign-up. The magazines send those e-mails, not this site. |
| [/feed.xml](https://neta65.github.io/aagrapevine/feed.xml), [/es/feed.xml](https://neta65.github.io/aagrapevine/es/feed.xml), [/events.ics](https://neta65.github.io/aagrapevine/events.ics), [/es/events.ics](https://neta65.github.io/aagrapevine/es/events.ics) | Ways to follow the site without e-mail: a news feed and a calendar. |
| **Actions → Monthly e-mail digest → a run** | Whether the e-mail was sent, previewed, waiting or failed ([3.14](#314-every-result-a-digest-run-can-show)). |
| **Issues** tab | The three automatic issues ([3.17](#317-the-three-automatic-issues)). |
| [/status/](https://neta65.github.io/aagrapevine/status/) | **Not** the e-mail. It shows the sources and the daily quote only. |

> Tip: until the e-mail is switched on, the chair can open [/digest/](https://neta65.github.io/aagrapevine/digest/),
> choose **Bilingual EN + ES**, press **Copy for e-mail** (under **More** on a phone) and paste the text into an
> ordinary e-mail to the group.

---

## 6. Going further: change the code

You can edit everything below on github.com: open the file, press the pencil, edit, then **Commit changes**. The
**Code check** then runs every test and builds a preview of the e-mail. A red ✗ means the change broke something.
To undo it, open the file's **History**, open the version from before your change, copy its text back into the file
and commit again. The live site keeps working either way. To find a spot in a long file, press
**Ctrl+F** and type the **search string** given in the tables. This guide never gives line numbers, because they
change.

**There is no separate template file.** The e-mail's HTML is written inside the Python functions `render_html()` and
`render_lang_html()`. The plain-text part is written in `render_text()`. All three are in
[`scripts/notify/send_digest.py`](../scripts/notify/send_digest.py).

### 6.1 A map of send_digest.py

| Search for | What it is |
|---|---|
| `T = {` | **Every fixed word** of the e-mail, in English (`"en"`) and Spanish (`"es"`): section titles, footer, buttons |
| `C = {` | The colours, the same as the website's light theme |
| `DRIVE_CATEGORIES` | The pill names of committee uploads, such as Reports / Informes and Flyers / Volantes |
| `FRESH_SOURCES` | The sources the e-mail waits for, with `FRESH_IDLE_DAYS = 3` |
| `def month_news(` | What counts as news in the month: the bulletin, uploads, albums, podcasts and the rest |
| `def month_events(` / `def meeting_by_rule(` | The events that took place, and the committee meeting row worked out from `meeting:` |
| `def event_row(` | How one event line is written (days only, never a time) |
| `def build_rows(` / `def item_meta(` / `def item_label(` | The rows for uploads, podcasts, videos and documents: pill, title and the small grey details |
| `def collect(` | Gathers the whole edition |
| `def subject_of(` | The subject line |
| `def render_html(` | The HTML frame: the masthead, the "English first" strip and the **footer** |
| `def render_lang_html(` | One language half of the HTML: every section and the two buttons |
| `def render_text(` | The plain-text part, including its footer |
| `def parse_recipients(` / `def build_message(` | Reads `DIGEST_TO`, and writes the headers (From, To, Reply-To, List-Unsubscribe) |
| `def connect(` / `def send(` | **The sending**: SMTP, encryption (465 = SSL, otherwise STARTTLS is required), login, 3 tries, and handing the message over once |
| `def waiting_for(` | The "wait for the data" rule |
| `def main(` | The command-line options, the order of the checks and the exit codes |
| `def send_prepared(` / `PREPARED` | The second half of a send on GitHub: `--prepare DIR` saves `message.eml` and `envelope.json` (nothing when nothing is new), and `--send-prepared DIR` hands that same e-mail to the server once (exit 0 sent, 4 it may have been sent, 1 not sent, 2 the mail settings are missing) |

The workflow file [`monthly-digest.yml`](../.github/workflows/monthly-digest.yml) holds the schedule
(`cron: "7 8,11,14,17,20 1-3 * *"`). Its step *"Is it time, and is the e-mail digest set up?"* holds the 7 AM rule
(`"$hour" -lt 7`), the on/off test (`if [ -z "$SMTP_SERVER" ]`), the marker check (skipped only with **force**) and the
noon-on-the-3rd rule. The steps after it build the e-mail (*"Build the digest (and decide whether to send it)"*),
save the "sending" marker, send it, and save the "sent" or "unsent" marker.

### 6.2 What to edit for each change

| To change… | Edit | Also keep in step, and the tests to watch |
|---|---|---|
| A fixed word or sentence, in either language | `T = {` in `send_digest.py`, both `"en"` and `"es"` | The website has its own copy in [`src/_i18n/community.json`](../src/_i18n/community.json), with keys `community.digest.*` such as `community.digest.toolkit_text`. Change it there too, so the page and the e-mail agree. `tests/test_send_digest.py` checks many exact sentences. |
| The subject | `def subject_of(` | `tests/test_send_digest.py`: `test_subject_and_preheader`, `test_dry_run_preview_in_both_languages` and `RealData` ([6.5](#65-example-put-neta-65-in-front-of-the-subject)) |
| The From name or the reply address | `site.committee` / `site.contact_email` in `config/site.yml`, or the secrets `DIGEST_FROM` / `DIGEST_REPLY_TO` | — |
| Who receives it | the secret `DIGEST_TO` (NETA65), or the Google Group | — |
| Rows per list, or stories per issue | `digest.per_section` / `digest.highlights` in `config/site.yml` | The page reads the same keys. |
| Header, logo, footer, buttons or colours | `def render_html(` (masthead, footer), `def btn(` inside `render_lang_html` (buttons), `C = {` (colours) | `test_every_text_has_enough_contrast`: every text must stay at least 4.5:1 against its background. |
| Add, remove or reorder a section | `def render_lang_html(` **and** `def render_text(` | The page: [`src/pages/digest.njk`](../src/pages/digest.njk) and `buildMonthlyDigest` / `monthlyDigestText` in [`community.js`](../eleventy/filters/community.js). The section order is tested in `test_dry_run_preview_in_both_languages`. |
| Add a detail to an event line (a time, for example) | `def event_row(` | Times are left out **on purpose** (see that function's comment), and `test_nothing_of_what_is_current` forbids "7:00 PM". Event details on the website: [Flyers and events](flyers-and-events.md). |
| Add a detail to an upload or podcast row | `def item_meta(`, `def item_label(`, `def build_rows(` | The page's `dgList` macro in `digest.njk` |
| What counts as news, or in which month | `def month_news(` (and `post_when`, `upload_when`) | **Must match** `monthNews` in `community.js`. `tests/test_digest_parity.py` fails if the two pick different items. |
| The "Coming up" row or the price row | `def toolkit_block(`, `def price_block(` (which row is due: `def price_change(`) | `community.js` (`buildMonthlyDigest` → `toolkit`), `digest.njk`. The `Digest` tests in `tests/test_price_changes.py` check that the e-mail and the page pick the same price row. |
| Which sources it waits for | `FRESH_SOURCES`, `FRESH_IDLE_DAYS` | the `Freshness` tests |
| Retries, timeouts, encryption | `def connect(`, `def send(` | the `Sending` and `SendFailure` tests |
| When it tries | the `cron:` line and the guard step in `monthly-digest.yml`. **Keep the 4-hours-early rule.** | `WorkflowSchedule` tests (the exact cron string is pinned); README → 10 c; `docs/OPERATIONS.md`. After a `cron:` change, redo the NETA65 Disable → Enable step. |
| The sending method itself (for example the Gmail API) | `def send(` and `def main(`, plus the workflow | [6.6](#66-if-you-want-the-gmail-api-oauth-instead) |

A wrong **Spanish title** in the e-mail is not fixed in this code. The e-mail takes titles already translated from the
site's data, so fix it in `data/translations/overrides.yml` ([Translations](translations.md)). The e-mail and the
page then both change.

### 6.3 Example: add the anonymity line to the plain-text footer

The HTML footer asks readers to protect anonymity, but the plain-text footer does not.

> Note: this is a small difference in the code as it is today. `render_html()` uses the `"footer_anon"` sentence
> (*"Feel free to forward it to your group or district — and please protect everyone's anonymity."*), but
> `render_text()` leaves it out.

1. Open `scripts/notify/send_digest.py`, and search for `T["en"]["footer_unsub"])`. You land at the end of
   `def render_text(`.
2. Change these two lines:

   ```python
       out.append(T["en"]["footer_why"].format(committee=committee) + " " + T["en"]["footer_unsub"])
       out.append(T["es"]["footer_why"].format(committee=site.get("committee_es") or committee) + " " + T["es"]["footer_unsub"])
   ```

   to:

   ```python
       out.append(T["en"]["footer_why"].format(committee=committee) + " " + T["en"]["footer_anon"] + " " + T["en"]["footer_unsub"])
       out.append(T["es"]["footer_why"].format(committee=site.get("committee_es") or committee) + " " + T["es"]["footer_anon"] + " " + T["es"]["footer_unsub"])
   ```

3. Commit. The preview's `digest.txt` now ends with these lines (checked against today's data):

   ```text
   You are receiving this monthly summary from the NETA 65 Grapevine & La Viña Committee. Feel free to forward it to your group or district — and please protect everyone's anonymity. To stop receiving it, reply with "unsubscribe".
   Recibes este resumen mensual del Comité de Grapevine y La Viña de NETA 65. Puedes reenviarlo a tu grupo o distrito — y, por favor, protege el anonimato de todos. Para dejar de recibirlo, responde con "cancelar".
   ```

4. Tests: no test checks the footer, so `python -m unittest tests.test_send_digest -v` stays green. The website's
   texts are not affected.

### 6.4 Example: change the "Coming up" sentence

The sentence under *"Coming up in October"* exists **three** times: twice in the e-mail (English and Spanish) and once
for the website. To change it:

1. In `scripts/notify/send_digest.py`, search for `"toolkit_text":`. It appears twice inside `T = {`, once under
   `"en"` and once under `"es"`. Edit both, for example:

   ```python
           "toolkit_text": "The committee meeting, events, story deadlines and this month's magazines.",
   ```

   ```python
           "toolkit_text": "La reunión del comité, los eventos, las fechas límite y las revistas de este mes.",
   ```

2. In `src/_i18n/community.json`, search for `"community.digest.toolkit_text"` and put the same two sentences there:

   ```json
   "community.digest.toolkit_text": { "en": "The committee meeting, events, story deadlines and this month's magazines.", "es": "La reunión del comité, los eventos, las fechas límite y las revistas de este mes." },
   ```

3. In `tests/test_send_digest.py`, search for `"COMING UP IN OCTOBER"` (the first of its two hits). The test
   `test_dry_run_preview_in_both_languages` expects the old English sentence word for word, split over two lines.
   Replace those two lines with one line holding the new sentence:

   ```python
                        "COMING UP IN OCTOBER", f"The committee meeting, events, story deadlines and this month's magazines. {SITE}/monthly/2026-10/"):
   ```

   No test checks the Spanish sentence, so this is the only test line to change.
4. Commit all three files together. The e-mail and [/digest/](https://neta65.github.io/aagrapevine/digest/) then say
   the same thing. Saving `community.json` starts a quick Website update, so the page changes within about 10 to 20
   minutes. Every text in `community.json` needs **both** languages. If the `"es"` text is missing, the page quietly
   shows the English one, and the **Code check** goes red (`tests/test_i18n_keys.py`). If a key is missing
   altogether, the website build fails and the old site stays up.

### 6.5 Example: put "NETA 65" in front of the subject

1. In `scripts/notify/send_digest.py`, search for `def subject_of(`. Change its last line to:

   ```python
       return f"NETA 65 {title} — {T['en']['edition'].format(month=month_label(k, 'en'))} · {T['es']['edition'].format(month=month_label(k, 'es'))}"
   ```

2. The subject becomes `NETA 65 Grapevine / La Viña — September 2026 digest · Resumen de septiembre de 2026`. The
   HTML `<title>` changes too, because it is the subject.
3. Update the tests in `tests/test_send_digest.py` that expect the old subject:
   - `test_subject_and_preheader`: two expected subjects;
   - `test_dry_run_preview_in_both_languages`: the `<title>…</title>` line;
   - `RealData.test_the_command_builds_a_preview`: the text `"DRY RUN — subject: Grapevine / La Viña — "`.

Changing `site.title` instead would rename the whole website, not only the e-mail.

### 6.6 If you want the Gmail API (OAuth) instead

**This does not exist in the repository today.** The SMTP method with an app password does the same job with less
setup, so it remains the recommended way. Consider the Gmail API only if Google stops offering app passwords to the
sending account, or if the committee does not want any password stored as a secret. Here is what would have to be
built.

**On Google's side (once):**

1. Open <https://console.cloud.google.com> and make a project. This is the same place as the optional
   `GOOGLE_API_KEY` in README 10 a, but a separate job. Then go to **APIs & Services → Library**, find **Gmail API**
   and press **Enable**.
2. Set up the **OAuth consent screen**:
   - For a **neta65.org** Workspace account, choose **Internal**. Google then does no review, and the tokens do not
     expire after a week.
   - For a free Gmail account, choose **External** and set the app to **In production**. Google's rule is that while
     an app is in "Testing", its tokens stop working after 7 days.
3. Go to **Credentials → Create credentials → OAuth client ID**. Note the **client ID** and the **client secret**.
   The type depends on how you will do step 4:
   - **Desktop app** if a short one-time script on a computer gets the token;
   - **Web application**, with `https://developers.google.com/oauthplayground` added under *Authorized redirect
     URIs*, if Google's **OAuth Playground** gets it. (Google's rule: the Playground cannot use a Desktop app client.)
4. Once, sign in as the sending account and allow only the scope `https://www.googleapis.com/auth/gmail.send`. This
   gives you a **refresh token**. In the OAuth Playground, open the settings (gear icon), tick
   "Use your own OAuth credentials" and paste the client ID and secret first.
5. The **NETA65** account adds three new secrets, for example `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` and
   `GMAIL_REFRESH_TOKEN`. The names are only suggestions: they must match what the code reads. `DIGEST_TO` stays as it
   is. Set `DIGEST_FROM` to the sending account's address, because the Gmail API sends **as** that account.

**In [`send_digest.py`](../scripts/notify/send_digest.py)**, using only Python's standard library:

1. Add `import base64`, `import urllib.error`, `import urllib.parse` and `import urllib.request` at the top.
2. Add a function like the sketch below, next to `def send(`. Like `send()`, it hands the message over **once**, and
   it raises `MaybeSent` when the answer never came, so exit code 4 keeps its meaning.

```python
def send_gmail_api(msg: MIMEMultipart, recipients: list[str]) -> None:
    """Hand the e-mail to the Gmail API (OAuth 2.0, scope gmail.send) instead of SMTP. (A sketch.)"""
    form = urllib.parse.urlencode({
        "client_id": os.environ["GMAIL_CLIENT_ID"].strip(),
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"].strip(),
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"].strip(),
        "grant_type": "refresh_token",
    }).encode()
    try:                                                 # 1. a fresh access token (nothing sent yet)
        with urllib.request.urlopen("https://oauth2.googleapis.com/token", form, timeout=60) as r:
            token = json.load(r)["access_token"]
    except (OSError, KeyError, ValueError) as e:
        raise RuntimeError(f"Could not get a Gmail API access token: {e}") from e
    if len(recipients) > 1:                              # the API reads the recipients from the headers;
        msg["Bcc"] = ", ".join(recipients)               # Gmail removes the Bcc line before delivery
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=json.dumps({"raw": raw}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:                                                 # 2. hand it over ONCE, like send() does
        urllib.request.urlopen(req, timeout=60).close()
    except urllib.error.HTTPError as e:                  # Google answered "no": not sent
        raise RuntimeError(f"The Gmail API refused the e-mail (HTTP {e.code}); it was not sent.") from e
    except urllib.error.URLError as e:                   # could not connect: not sent
        raise RuntimeError(f"Could not reach the Gmail API: {e.reason}") from e
    except OSError as e:                                 # the answer never came: it MAY have been sent
        raise MaybeSent(f"The connection failed while the e-mail was being handed over ({e}).") from e
```

3. At the start of `def send(`, choose the method:
   `if os.environ.get("GMAIL_REFRESH_TOKEN", "").strip(): return send_gmail_api(msg, recipients)`.
4. In `def send_prepared(` and in `def main(`, the lines with `missing = … ("SMTP_SERVER", "SMTP_USERNAME",
   "SMTP_PASSWORD")` must accept the three Gmail secrets instead of the SMTP ones. Otherwise the run stops with
   "not configured" (exit 2).
5. One side effect: with several recipients, the **To:** line holds the committee's own address, so that address
   would also receive a copy through the API. With SMTP it does not.

**In [`monthly-digest.yml`](../.github/workflows/monthly-digest.yml):**

- In the first step, change the on/off test (search for `if [ -z "$SMTP_SERVER" ]`) so that `DIGEST_TO` plus the
  Gmail secrets also count as "set up". Add `GMAIL_REFRESH_TOKEN: ${{ secrets.GMAIL_REFRESH_TOKEN }}` to that step's
  `env:`.
- In the step *"Send the digest"* (since October 2026 the e-mail is built in *"Build the digest (and decide whether
  to send it)"* and sent in that next step, `send_digest --send-prepared`), add all three secrets to `env:`.

**Tests and documents:**

- Add tests to `tests/test_send_digest.py` with a fake `urlopen`, in the same way the `Sending` tests use `FakeSMTP`.
- Update README → 10 c, `docs/SETUP-GITHUB.md` (*Where to add secrets*), `docs/OPERATIONS.md` (*Environment variables
  and secrets*) and this guide.

**Good to know:** Google also cancels OAuth tokens that carry Gmail permissions when the account's password changes.
So the API needs looking after too, like an app password.

### 6.7 Run the tests

You do not have to run anything yourself. Every push that changes code, settings, content, tests or a workflow (for
example a file in `scripts/`, `config/`, `content/`, `src/`, `tests/` or `.github/workflows/`) starts the **Code
check**, which runs all the tests and builds a preview of the e-mail.

On a computer with the project set up (see [Automation and troubleshooting](automation-and-troubleshooting.md)):

```powershell
python -m unittest discover -s tests                 # everything, as the Code check runs it
python -m unittest tests.test_send_digest -v         # the e-mail only (a few seconds)
python -m unittest tests.test_digest_parity -v       # e-mail vs /digest/ page (needs Node.js and "npm ci", else skipped)
python -m scripts.notify.send_digest --dry-run       # look at .tmp\digest.html afterwards
```

The main test groups in `tests/test_send_digest.py` are:

| Test group | What it checks |
|---|---|
| `EditionWindow` | which month an edition covers, in Central time |
| `Sections` | the sections and their order, the wording, the contrast of the colours, what must never be in the e-mail, and "nothing new means no e-mail" |
| `Wording` | small wording rules: page counts, Spanish months inside a line, La Viña's issue names, the Weekly Open pill, the committee meeting rule |
| `PostMarkdown` | how a bulletin post's Markdown is drawn in the HTML and the text part, phone links, and where a long post is cut |
| `Sending` | the password is only sent over an encrypted connection, and retries happen only before the message goes |
| `MonthArgument` | a mistyped month stops the run, and a month that is not over is not sent |
| `Freshness` | the wait for the data |
| `SendFailure` | the exit codes 1 and 4 |
| `WorkflowSchedule` | the exact cron line, the guard, the markers (sending, sent, unsent), **force**, and each step's conditions and order |
| `RealData` | the preview command works on the repository's real data |

---

## 7. Troubleshooting

**Where problems are reported:** the digest run's page, in its summary, annotations and the logs of *"Build the
digest (and decide whether to send it)"* and *"Send the digest"*; GitHub's failure e-mail for red runs; the **Issues** tab; cron-job.org's e-mails and the job's
**History**. The digest is never on `/status/`.

| Symptom | Likely cause | Fix |
|---|---|---|
| Every try on the 1st to the 3rd says *"E-mail digest is off"* | A required secret is missing, or was saved somewhere other than **Repository secrets** (as a Variable, or as an Environment secret, for example). | NETA65 adds `SMTP_SERVER`, `SMTP_USERNAME`, `SMTP_PASSWORD` and `DIGEST_TO` under **Settings → Secrets and variables → Actions → Secrets** ([3.3](#33-the-secrets)). |
| Red: *"The mail server rejected the username/password … App Password …"* | The normal Google password was used; the app password was deleted; the Google password was changed (which cancels app passwords); a space or line break was pasted; or `SMTP_USERNAME` is not the full address. | Make a new app password and **Update** `SMTP_PASSWORD` with only the 16 letters ([3.15](#315-change-the-password-or-the-recipients-or-stop-the-e-mail)). |
| Red: *"Could not reach the mail server …"* | `SMTP_SERVER` is misspelled, or the port is wrong. | Fix the secret. Use `smtp.gmail.com` with port 587 (empty) or 465. |
| Red: *"… does not offer STARTTLS; refusing to send the password unencrypted …"* | The port is not 587 or 465, or the server offers no encryption. | Set `SMTP_PORT` to `587`, or to `465` for "SSL". |
| Red: *"invalid literal for int() …"* | `SMTP_PORT` holds a word, not a number. | Make it `587` or `465`, or delete it. |
| Red, and the log says *"e-mail is not configured (missing: DIGEST_TO)"* | `DIGEST_TO` has no valid address, for example addresses separated only by spaces. | Separate the addresses with commas, semicolons or new lines ([3.6](#36-who-receives-it)). |
| Red: *"Stopped: the month '2026-9' is not a YYYY-MM month …"* | The month box was mistyped. | Type `2026-09`, or leave the box empty. |
| Red: *"Not sent: October 2026 is not over yet …"* | A send was tried for the current month. | Tick **Preview only** to look at it, or wait for the 1st. |
| Green: *"Digest waits"* / *"waiting for the data"* | The month's first full update has not finished yet. | Nothing to do: a later try sends it, and from noon Central on the 3rd it goes out anyway. |
| Green: *"Nothing new in September 2026 — no e-mail sent."* | Nothing was added that month. Events alone do not count. | Nothing to do. If that is wrong, check the sources on `/status/`: a stopped source has no new items. |
| Green *"sent"*, but nobody received it | The Google Group held the message (moderation) or refused the sender (posting permissions), or spam filters took it. | Check the group's pending messages and settings ([3.6](#36-who-receives-it)), the sending account's **Sent** folder, and the bounce messages in its inbox. |
| Red: ❌ *"The digest MAY have been sent"* | The connection broke while the e-mail was being handed over. The month is marked as done. | Check the group and the Sent folder. Send by hand with **force** ([3.12](#312-send-a-month-by-hand)) **only** if it is missing. |
| Red: ❌ *"The digest was not sent"* | The mail server took nothing (a wrong password, server or address: the *"Sending FAILED"* line in the log of *"Send the digest"* says which). | Fix the cause; the next try sends it ([3.14](#314-every-result-a-digest-run-can-show)). |
| Yellow ⚠️ *"Digest send not confirmed"* on every try | A send was cut off (cancelled, out of time) between *"Mark the month as being sent"* and the marker after the send, so the e-mail may have gone. Nothing is sent again by itself. | Check the group. If it arrived, nothing to do. If not, **Run workflow** with *Preview only* unticked and **force** ticked. |
| Yellow ⚠️ *"Already sent"* after **Run workflow** | That month went out already. | Nothing, or tick **force** to send it again. |
| The districts got the e-mail **twice** | Someone sent it again with **force**, someone deleted the sending run during the 1st to the 3rd, or a leaked alarm key was used. | See the note in [3.9](#39-when-it-goes-out-the-schedule-and-its-safety-rules). Preview before any manual send, and keep the alarm key private. |
| No digest run at all on the 1st to the 3rd | GitHub skipped the timed runs, or the workflow is disabled (for example by the 60-day rule). | **Actions → Monthly e-mail digest**: press **Enable workflow** if it shows as disabled, then send by hand. |
| The e-mail shows the Gmail address as **From**, not `grapevine@neta65.org` | That is normal with a Gmail account. Gmail replaces a From address that is not the account or a verified alias. | Replies still go to `grapevine@neta65.org` (the Reply-To). To send **from** a neta65.org address, see [3.5](#35-send-from-the-neta65org-mailbox-or-another-mail-host). |
| The **To:** line shows the committee's own address | Several addresses are in `DIGEST_TO`. They are given only to the mail server. | Nothing to do. Nobody sees the other addresses. |
| A Spanish title in the e-mail is wrong | A machine translation | Fix it in `data/translations/overrides.yml` ([Translations](translations.md)). |
| A bulletin post is missing from the e-mail | It was counted in another month (the month it was **added** to the site), or it **expired** before the e-mail was built. A post that expires on the last day of the month is left out of the e-mail built on the 1st to the 3rd. | Let `expires` / "(until …)" run past the 3rd of the next month ([Bulletin](bulletin.md)). |
| An event is missing from "Events in …" | It started in another month, or it never reached the events data. | [Flyers and events](flyers-and-events.md) |
| Red runs keep e-mailing **MKP715**, and NETA65 gets nothing | The timed workflows were last switched on from MKP715. | Do the owner step in [3.16](#316-githubs-run-failed-e-mails) as NETA65. |
| Nobody was told about *"A content source has stopped updating"* or *"The website update keeps failing"* | Nobody watches the repository, or watching e-mails are off. | Press **Watch → All Activity**, and tick **Settings → Notifications → Watching → Email** ([3.17](#317-the-three-automatic-issues)). |
| A *"Broken links found by the weekly check"* comment arrives every Sunday | A link in `config/site.yml` or in a `content/` file is broken. | Fix the address. The issue closes by itself after a clean Sunday. |
| cron-job.org reports 401, 403, 404 or 422 | The key expired, its permission is wrong, the URL is wrong, or the body is wrong (or the Morning check is off). | See the table in [3.18](#318-the-morning-alarm-cron-joborg). |

> **Public logs:** this repository is public, so its run logs and summaries are public too. They show only the
> **number** of recipients. The one exception is *"All recipients were refused: [ … ]"*, which lists the refused
> addresses. One more reason to use a single Google Group address.

---

## 8. Good practice and AA principles

- **Anonymity travels with the e-mail.** The digest can be forwarded anywhere, so anything in a bulletin post reaches
  inboxes outside the committee. Never put a member's full name, or a face, in a post or a photo. The e-mail never
  adds the meeting's Zoom link, passcode, phone numbers or event times (a test enforces this), but a post's own text
  goes out as written. Writers are shown the way the magazines print them, by first name and last initial. The HTML
  footer asks readers to protect everyone's anonymity.
- **Everything in the Drive folder is public**, and so is everything in the e-mail. Committee-upload rows link
  straight to the Drive files. Put nothing in the panel folder that could not go out to every district. Google's own
  page for a shared file can also reveal which account owns it, so keep the panel folder and its files owned by a
  committee account, not a personal one.
- **Attraction rather than promotion.** One plain recap a month, sent once, and easy to leave. Act on every
  "unsubscribe" or "cancelar" reply promptly.
- **Keep addresses private.** Use a Google Group, and never write an address list into a repository file: the
  repository is public, and `DIGEST_TO` is a secret for that reason.
- **Use committee accounts, not personal ones.** The sending Google account, the GitHub owner (NETA65) and the
  cron-job.org account should all belong to the committee, so that service can rotate without losing access. Hand
  over the passwords in person when the chair changes.
- **Treat app passwords and keys like cash.** Never paste one into an issue, a file, a chat or an e-mail. Renew
  them yearly, and delete them when someone leaves.
- **Preview before you send by hand.** A manual send cannot be taken back, and it reaches every district.

## 9. See also

- [How-to index](README.md) shows the big picture and who can do what.
- [Automation and troubleshooting](automation-and-troubleshooting.md) covers every workflow, manual runs, run
  summaries, `/status/` and running things on a computer.
- [Settings](settings.md) explains `config/site.yml`, including `site:`, `meeting:`, `price_changes:` and `digest:`.
- [Bulletin](bulletin.md) explains how posts are counted, pinned and expired, and therefore what reaches the e-mail.
- [Flyers and events](flyers-and-events.md) covers the events that appear under "Events in …".
- [Photos, slides and reports](photos-slides-reports.md) and [Drive panel folder](drive-panel-folder.md) cover the
  committee uploads.
- [Automatic sources](automatic-sources.md) covers the magazines, writers, podcasts, videos, Instagram and documents.
- [Translations](translations.md) explains how to fix a Spanish or English title everywhere.
- [Pages and code](pages-and-code.md) covers the `/digest/` page and the site's templates.
- [Booth display](booth.md) covers the booth folder and the booth display (nothing of it is in the digest).
- [File types](file-types.md) and [Presentations](presentations.md) cover the other kinds of committee files.
- The code and settings: [send_digest.py](../scripts/notify/send_digest.py),
  [monthly-digest.yml](../.github/workflows/monthly-digest.yml), [update.yml](../.github/workflows/update.yml) (the
  stale-source issue), [link-check.yml](../.github/workflows/link-check.yml),
  [morning.yml](../.github/workflows/morning.yml), [config/site.yml](../config/site.yml),
  [digest.njk](../src/pages/digest.njk), [test_send_digest.py](../tests/test_send_digest.py) and
  [test_digest_parity.py](../tests/test_digest_parity.py).
- The repository's own documents:
  - [README → 10 c, Monthly e-mail digest](../README.md#c-monthly-e-mail-digest-keep-every-district-informed)
  - [README → 10 d, The morning alarm](../README.md#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended)
  - [README → 8, Is everything working?](../README.md#8-is-everything-working)
  - [README → 14, Housekeeping](../README.md#14-housekeeping)
  - [docs/SETUP-GITHUB.md → Where to add secrets](../docs/SETUP-GITHUB.md#where-to-add-secrets)
  - [docs/OPERATIONS.md → monthly-digest.yml](../docs/OPERATIONS.md#monthly-digestyml)
