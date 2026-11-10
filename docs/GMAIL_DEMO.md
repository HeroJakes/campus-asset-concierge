# Gmail code email for the demo

Optional Gmail API delivery uses one authorized sender account. Gemini Enterprise
is not required. Borrowers only receive email; they do not connect their accounts.
Use controlled team inboxes with the fictional borrower accounts.

The implementation is merged and deployed as of November 10. Sender authorization
and receipt of a direct test email by Borrower A are verified. Automatic pickup and
return code delivery still needs a live rehearsal. See [release evidence](OPERATIONS.md#november-10-release).

## Authorize the sender

1. In [Google Cloud Console](https://console.cloud.google.com/), select your project
   and enable **Gmail API** under APIs & Services.
2. Open **Google Auth Platform**. Set the app name and contact email. For a personal
   Gmail sender, use an **External** audience and keep the app in **Testing**.
   Add the sender's Gmail address as a test user.
3. Under **Data Access**, add only
   `https://www.googleapis.com/auth/gmail.send`. This grants sending access, not
   permission to read the inbox.
4. Under **Clients**, create a **Web application** OAuth client. Add this authorized
   redirect URI: `https://developers.google.com/oauthplayground`.
5. Open [OAuth Playground](https://developers.google.com/oauthplayground). In its
   settings, enable **Use your own OAuth credentials** and enter the client ID and
   client secret. Keep offline access enabled.
6. Enter the send-only scope above and select **Authorize APIs**. Sign in as the
   sender and approve sending access for your test app.
7. Select **Exchange authorization code for tokens**. Save the refresh token
   privately. Do not paste credentials into chat, screenshots, Git, or PRs.

Google may show an unverified-app notice for your own test app. Only continue if
the project, app, sender account, and send-only permission are the ones you chose.
External apps in Testing normally get refresh tokens that expire after **seven
days**. Repeat authorization near the demonstration if necessary.

## Configure locally

Add these values to the ignored `.env`; replace all example addresses and values:

```dotenv
GMAIL_SENDER=sender@gmail.com
LOCAL_BORROWER_A_EMAIL=borrower-a@example.com
LOCAL_BORROWER_B_EMAIL=borrower-b@example.com
GMAIL_OAUTH_JSON='{"client_id":"YOUR_CLIENT_ID","client_secret":"YOUR_CLIENT_SECRET","refresh_token":"YOUR_REFRESH_TOKEN"}'
```

The sender must be the account authorized above. Never use your Gmail password or
the Firebase service-account key. Restart `uv run dev` after changing `.env`.
To disable email, leave `GMAIL_SENDER` empty.

For an approved hosted release, add the same values as private Production
environment variables. Enter the JSON value without the surrounding shell quotes.
Do not deploy or change hosted secrets as part of local testing.

## What happens

- Staff loading saves the pickup code, then sends its email.
- Requesting a return saves the code and compartment, then sends its email.
- Emails contain the existing code, item, location, compartment, and validity
  times. Times follow the simulated clock shown by the app.
- Delivery state lives inside the access record. A transaction claims the send,
  then Gmail is called outside the transaction. Repeating a completed action does
  not send another copy. No email runs from model or public MCP tools.
- The borrower sees Gmail acceptance or a failure message. **Email my code**
  retries a definite failure using the same code, after checking ownership,
  expiry, failed attempts, and whether the code was used.
- Gmail acceptance does not guarantee inbox delivery. Check spam too. On a
  timeout or server error after sending starts, the app reports an unknown result
  and does not resend automatically. Check the sender's Sent folder manually.
- If a process stops after claiming delivery, the record stays `sending`. Staff
  must check the sender's Sent folder; automatic recovery is outside this demo.
- Code lookup through the borrower's `/pickups` or `/returns` remains available.
  Codes and recipient addresses are not included in model status results.

This is synchronous delivery for a handful of demo messages, with five-second
timeouts on token refresh and sending. A production rollout needs a durable email
worker and a reviewed recovery process for uncertain delivery. Do not reset demo
state while an email is sending: a reset can invalidate its saved code.

## Check it

Automated tests mock Gmail and run against both emulator storage layouts. They
never send real emails. For a real check, use an emulator scenario and the supplied
team inboxes. Load one kit and request one return, then confirm receipt and try the
codes. Repeat each action to check that it does not send duplicate emails.

The current Google quota page says usage below the daily billing threshold incurs
no extra charges. Five to ten demo messages are far below that threshold. Existing
Gmail account sending limits still apply.

Sources: [sending email](https://developers.google.com/workspace/gmail/api/guides/sending),
[send-only permission](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send),
[offline authorization](https://developers.google.com/identity/protocols/oauth2/web-server),
[test-token expiry](https://developers.google.com/identity/protocols/oauth2#expiration),
[usage limits](https://developers.google.com/workspace/gmail/api/reference/quota).
