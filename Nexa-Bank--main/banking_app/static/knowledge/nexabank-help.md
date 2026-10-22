# NexaBank Help Knowledge Base

This document is the local source of answers for the NexaBank help chatbot.
Keep each article self-contained. Answers must describe implemented app behavior,
avoid financial advice, and never include secrets or real customer information.

## About NexaBank
Answer: NexaBank is an educational simulation. It does not connect to a real bank or move real money. Please use only fictional information.
Keywords: demo simulation real money external bank fake information safety privacy
Details: The app README describes NexaBank as an educational banking simulation and warns users not to enter real personal or financial information.
Link: /
Link label: About NexaBank

## Transfer money
Answer: Open Transfer, enter the recipient and account number, confirm the account number, choose a transfer type, then enter and submit the amount. Transfers are simulated and do not send real money.
Keywords: send pay recipient account number confirm bank upi transfer money move
Details: The transfer flow validates the recipient name, account number confirmation, amount, and available balance before recording a simulated transaction.
Link: /transfer
Link label: Open Transfer

## Deposit money
Answer: Use Deposit to record an amount and method. This is a simulated entry; no external payment provider is contacted.
Keywords: add funds add money credit cash deposit payment provider real external
Details: Deposits create a credit entry in the simulation ledger and do not contact an outside payment service.
Link: /deposit
Link label: Open Deposit

## Withdraw money
Answer: Use Withdraw to record the amount and method. The amount must be a multiple of ₹5, within the per-transaction limit, and no greater than your available account balance.
Keywords: cash atm take out withdraw withdrawal multiple five 5 limit available balance
Details: The withdrawal route validates positive amounts, the ₹5 multiple constraint, configured transaction limit, and account balance.
Link: /withdraw
Link label: Open Withdraw

## Transaction history
Answer: Open Transaction History to browse account activity. Select an item to view its details and available receipt options.
Keywords: transactions history activity payments past receipt details search
Details: Transaction history is account-specific and displays recorded transaction status, type, amount, and details.
Link: /transactions
Link label: View transaction history

## Accounts and balances
Answer: Your Dashboard summarizes balances. Open Accounts for account details; account numbers are masked for privacy.
Keywords: balance account funds available total masked number details dashboard
Details: Account pages display account details and masked account numbers. Balance information reflects the records in this simulation.
Link: /accounts
Link label: View Accounts

## Analytics
Answer: Analytics shows recorded income, expenses, net cash flow, savings rate, spending categories, and balance movement. You can change the time range at the top of the page.
Keywords: analytics analysis chart graphs income expenses spending category cash flow savings rate trend period monthly
Details: Supported time ranges are 7 days, 30 days, 6 months, and 1 year. Analytics is calculated from recorded account transactions.
Link: /analytics
Link label: Open Analytics

## Statements and PDF downloads
Answer: Open Statements to view activity for a date range or download a PDF. The default range is the last 30 days.
Keywords: statement pdf download export date range report document
Details: Statement downloads contain the account's transactions for the selected date range.
Link: /statements
Link label: Open Statements

## Change your password
Answer: Open Profile & Settings → Change password. Enter your current password, then enter and confirm a new password that meets the strength requirements.
Keywords: password change update sign in login credential security
Details: The change-password form requires the current password, server-side password-strength validation, and matching new-password confirmation.
Link: /profile#password-settings
Link label: Open password settings

## Forgot password
Answer: Use the Forgot password link on the sign-in page to open the recovery flow.
Keywords: forgot password recover reset login sign in cannot access
Details: Password recovery is available from the sign-in page.
Link: /auth/login
Link label: Go to sign in

## Change transaction PIN
Answer: Open Profile & Settings → Change transaction PIN. You will need your current PIN and must enter the new 4-digit PIN twice.
Keywords: pin transaction pin number change update four digit 4 security
Details: The PIN change form verifies the current PIN and validates that the new PIN is four numeric digits and matches the confirmation.
Link: /profile#security-settings
Link label: Open PIN settings

## Theme and profile settings
Answer: Open Profile & Settings to update your profile details or select a light or dark theme.
Keywords: profile settings theme appearance dark light name address city state postal code
Details: Profile settings support updating name and address fields and selecting light or dark appearance.
Link: /profile
Link label: Open Profile & Settings

## Identity verification documents
Answer: Identity and address proof are required during registration; a photograph is optional. Supported formats are PDF, JPG, JPEG, and PNG, up to 5 MB each. Documents stay pending until an administrator reviews them. Check their status in Profile & Settings.
Keywords: kyc identity verification upload file document address proof photograph photo pdf jpg jpeg png size 5mb pending rejected verified admin status
Details: Uploaded documents are encrypted at rest, and only the owner or an administrator may retrieve them. Administrators can review, verify, reject with a reason, or delete documents. Do not use real identity documents for local development or UI testing.
Link: /profile#privacy-settings
Link label: View verification status

## Notifications
Answer: Open Notifications to review account updates. You can mark a notification or all notifications as read.
Keywords: notifications alerts messages unread read updates
Details: The notifications page lists updates for the signed-in user and supports marking them as read.
Link: /notifications
Link label: Open Notifications

## Create an account
Answer: Choose Create Account and complete the registration form, including required identity and address documents. After successful registration, you are sent to sign in.
Keywords: register registration create account signup sign up new user identity address terms login
Details: Registration validates the submitted details, credentials, transaction PIN, terms acceptance, and required documents. Successful registration does not automatically sign the user in.
Link: /auth/register
Link label: Create an account

## Contact and support scope
Answer: This assistant searches the app's local help guide. It is not a live agent or financial advisor and cannot access private account data.
Keywords: support contact help agent human live financial advice advisor private account data
Details: The chatbot retrieves answers from this local knowledge document in the browser. It does not send questions to an external AI service or access user-specific account and transaction records.
Link: /
Link label: About NexaBank
