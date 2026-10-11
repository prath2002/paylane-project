# Note to the Paylane support team

This note explains, in plain words, what the support agent does, what it won't do, and what we need from you before it goes live.

## What it does

- **Checks who it's talking to first.** The customer gives the email on their account and the last 4 digits of their card. Nothing about the account is discussed until both match.
- **Refunds small, recent purchases on the spot.** If a purchase is $75 or less, under 30 days old and hasn't been refunded already, the agent refunds it and gives the customer a refund number.
- **Explains why a card is frozen.**
- **Passes everything else to your team.** It opens a ticket with a short summary and gives the customer the ticket number. This covers:
  - refunds over $75 or older than 30 days
  - fraud reports
  - legal threats
  - requests to close an account
  - requests to unfreeze a card

## What it won't do

- **Refund anything outside the rules, however hard the customer pushes.** "Just refund $75 of it" doesn't work.
- **Unfreeze a card, close an account, or promise when your team will reply.**
- **Share account details with someone who isn't verified**, or repeat a customer's email or card digits.
- **Help someone acting for another person**, or anyone claiming to be Paylane staff.
- **Let someone keep guessing.** After 3 wrong tries it stops and passes the case to your team.

## How we tested it

We wrote 13 conversations designed to catch it out:
- angry customers
- people pretending to be staff or family
- refunds that are exactly at the limit, just over it, or exactly 30 days old
- frozen cards, fraud, and legal threats

Each one ran 3 times, and the agent handled all 39 correctly.

Testing also found a real problem early on: the agent agreed to refund $75 of a $120 purchase. That is fixed, and the test that caught it now runs every time. The full results are in `EVAL.md` and the conversations are in `TRANSCRIPTS.md`.

## What we need from you before launch

1. **Confirm four choices we made.**
   - Every fraud report goes to your team, not only ones over $500.
   - Verification stops after 3 wrong tries.
   - The agent won't help family members acting for a customer.
   - The agent tells customers their card was frozen after a fraud alert.
2. **A reply time we can promise**, if you have one. For now customers only hear "a person will follow up."
3. **Who picks up the tickets**, and how many a day your team can handle.
4. **20–30 real past chats**, with personal details removed, so we can test the agent on how your customers actually write.
5. **A small first launch.** For example, 10% of chats for two weeks, with someone on your team reading a sample each day.
