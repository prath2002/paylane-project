# Decisions

The policy brief leaves some cases open. This file lists every decision made while building the agent, why it was made, and what it is based on. Each one is a constant or a few lines of code, so any of them can be changed quickly.

## Refunds

### 1. The $75 limit applies to the transaction, not the refund
- **Decision:** If a transaction is over $75, the whole transaction goes to a human. The agent does not refund part of it, so "just refund $75 of my $120" is refused. A transaction of exactly $75.00 is refunded.
- **Why:** If partial refunds were allowed, any large transaction could be refunded $75 at a time, which makes the limit meaningless.
- **Based on:** The policy says "Above $75 … escalate". Eval conversation 03 showed that the first version of the agent refunded $75 of a $120 transaction when the customer asked (see `EVAL.md`). Tested with T101 ($120) and T104 (exactly $75).

### 2. "Under 30 days" is counted from the purchase date, and day 30 is out
- **Decision:** A transaction's age is today minus its purchase date. Exactly 30 days old is refused and sent to a human.
- **Why:** "Under 30" means 29 days or less. The purchase date is the date the customer knows and the date the mock data stores.
- **Based on:** The policy wording ("under 30 days old"), and the `date` field in `get_transaction`. Tested with T102 (exactly 30 days old).

### 3. One refund per transaction, partial refunds only on transactions of $75 or less
- **Decision:** After any refund the transaction is marked `refunded`, and no further refund is possible on it.
- **Why:** This is the simplest rule that can never pay out the same transaction twice.
- **Based on:** The policy says "Never refund the same transaction twice". Tested with T103 (already refunded) and a second partial refund on T100.

### 4. Pending transactions are not refunded
- **Decision:** The agent tells the customer it can be refunded once it settles. It is not escalated.
- **Why:** Money that hasn't settled may still change or be reversed, and refunding it could pay out twice.
- **Based on:** The API has three statuses (`settled`, `pending`, `refunded`), and only `settled` money has definitely moved. Tested with T301.

### 5. No refunds on a frozen card
- **Decision:** Refunds are refused while the card is frozen, and the customer is escalated if they want it unfrozen.
- **Why:** A card is usually frozen because of a fraud alert. Moving money on it before a person has reviewed it is risky.
- **Based on:** The policy says the agent "cannot unfreeze" and must escalate. The mock reason for C002's freeze is a fraud alert. Tested in conversation 09.

### 6. The agent knows whether a refund is allowed before it tries
- **Decision:** `get_transaction` also returns `auto_refund: {allowed, reason}`. The agent calls `issue_refund` only when `allowed` is true.
- **Why:** The policy says the agent "must not call issue_refund when the policy says no". To do that, it needs the answer first. `auto_refund` and `issue_refund` use the same function (`_refund_block_reason`), so they can never disagree, and `issue_refund` still checks again in case the model ignores the rule.
- **Based on:** In the first eval run the agent called `issue_refund` on forbidden refunds in 4 conversations (03, 04, 09, 11). After this change it happened in none of the 39 final runs. A unit test checks that the two always agree.

### 7. A refund is only confirmed after the tool says it worked
- **Decision:** The agent tells the customer a refund is done only when `issue_refund` returns `ok: true`, and it gives the refund id.
- **Why:** A false "your refund is done" is worse than a delay.
- **Based on:** The policy says "Never promise things the policy doesn't allow". Every conversation in the eval checks for this.

## Verification and privacy

### 8. The tool compares the card digits, not the model
- **Decision:** `get_customer` takes the email and the last 4 digits the customer gave, and says only whether they match. It never returns the email or the card digits.
- **Why:** If the model never sees the real digits, it can't reveal them, even if it's tricked.
- **Based on:** The policy says "Never reveal full card numbers or the email itself". The mock API returns `card_last4`, which would put the real digits in front of the model.

### 9. Verification locks after 3 failed attempts in a chat
- **Decision:** After 3 wrong attempts, `get_customer` refuses, even if a later guess is correct, and the agent escalates. The count covers the whole chat, so trying different emails doesn't reset it.
- **Why:** The last 4 digits are printed on receipts, and emails are easy to find. With no limit, anyone could guess their way into an account.
- **Based on:** Eval conversation 08: in the first version, a person claiming to be the customer's husband guessed digits until the 4th guess verified him. Tested in conversation 13 and in unit tests.

### 10. An unknown email gets the same answer as wrong digits
- **Decision:** Both return "details didn't match" and count as a failed attempt.
- **Why:** Otherwise the chat could be used to check whether someone has a Paylane account.
- **Based on:** Standard practice for login and verification flows. Tested in unit tests.

### 11. Only the account holder is helped
- **Decision:** Someone asking on behalf of a partner, relative or friend is asked to have the account holder get in touch. Claiming to be Paylane staff changes nothing.
- **Why:** Knowing someone's email and card digits doesn't make it your account.
- **Based on:** Eval conversations 07 (fake "fraud team" member) and 08 (the "husband").

### 12. The agent never repeats the card's last 4 digits or the email
- **Decision:** It doesn't repeat them even to the person who just typed them.
- **Why:** A transcript or screenshot of the chat could leak them. There's no reason to show them back.
- **Based on:** The policy forbids revealing the email and full card number. The same idea is extended to the last 4 digits. Every conversation in the eval checks for this.

## Escalation

### 13. Every fraud report goes to a human, not only those over $500
- **Decision:** Any report of fraud, an unauthorized charge or a stolen card is escalated.
- **Why:** The agent has no tool to investigate fraud. Below $500 it would just be guessing.
- **Based on:** The policy requires a human for fraud over $500 and says nothing about smaller amounts, and the four tools can't investigate. If small disputes should be handled as normal refunds instead, that's a one-line prompt change.

### 14. The agent can say why a card is frozen
- **Decision:** It explains the reason on file, for example "frozen after a fraud alert on 2 Oct".
- **Why:** The customer needs to know what's going on. Explaining is allowed; unfreezing is not.
- **Based on:** The policy says the agent "can explain why a card is frozen". The mock API has no field for the reason, so `frozen_reason` was added to the mock data.

### 15. Legal threats are escalated even when the customer isn't verified
- **Decision:** The agent escalates with customer id `unknown` and shares nothing about any account.
- **Why:** Legal threats have to reach a person whoever sends them, but an unverified person mustn't learn anything about an account.
- **Based on:** The policy says "anything about legal action … goes to a human". Tested in conversation 12.

### 16. No promised reply times or outcomes
- **Decision:** After escalating, the agent says a person will follow up and gives the ticket id. It never says when, and never says what the outcome will be.
- **Why:** The policy doesn't give a reply time, so any time would be made up.
- **Based on:** The policy says "Never promise things the policy doesn't allow". Every conversation in the eval checks for this.

### 17. Escalation is the agent's choice, checked by the eval
- **Decision:** `escalate_to_human` always succeeds. When to escalate is set in the prompt, not enforced in code.
- **Why:** Deciding whether a message is a legal threat or a fraud report needs language understanding, so it can't be a simple code rule. Instead, every escalation case is checked in the eval.
- **Based on:** Eval conversations 03, 04, 09, 11, 12 and 13 all check that an escalation happened.

## Test setup

### 18. Today's date is fixed at 2026-10-10
- **Decision:** `TODAY` in `tools/api.py` is fixed instead of reading the clock.
- **Why:** The 30-day rule gives the same result every time the tests run.

### 19. A third test customer was added
- **Decision:** Meera (C003), with a $640 transaction for the fraud case and a pending transaction.
- **Why:** The original mock data had no transaction over $500 and none still pending.

### 20. "Not found" and "someone else's transaction" give the same error
- **Decision:** `get_transaction` returns "transaction not found on this account" in both cases.
- **Why:** Otherwise it would reveal which transaction ids exist on other accounts.
