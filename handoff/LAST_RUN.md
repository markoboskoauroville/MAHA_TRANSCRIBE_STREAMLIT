# STEP: the owner's gold edge, and why the admin tools vanished
STATUS: done, pushed as v108

WHAT HAPPENED
- The whole panel gets a gold border when the owner is signed in. It
  uses var(--amber), the SAME token as the signature at the foot, so the
  edge and the word `admin` are one colour by construction rather than a
  hex copied twice and drifting when the scheme changes.
- WHY THE ADMIN TOOLS DISAPPEARED, and it is not a bug in the app:
  is_admin() compares the logged-in USER against ADMIN_USER from the
  Streamlit secrets. Baba now logs in as the NAME `admin`, but that
  secret still holds his old PASSWORD. Name vs password, so the check
  fails and the second gear and L are not drawn. The fix is one line in
  the cloud secrets: ADMIN_USER = "admin". Nothing to change in code.

NUMBERS
- owner edge 5 · calm login 32 · login 7 · engine UI 18 — all green
- one mutation applied (give the edge to everyone) and caught
- pyflakes clean across app.py and ttt/

WHAT BROKE, AND WHAT I UNDID
- The edge was first written as a parameter on theme.css(). That
  stylesheet is emitted before anyone has logged in, so it can never
  know who this is — the flag would have been False on the one run that
  matters. Reverted, and it is one rule emitted after authentication
  instead.
- My first test helper matched any markdown containing "block-container"
  and so found the MAIN stylesheet, which styles that class too. Every
  check passed for everybody and the mutation changed nothing. It now
  matches the exact rule.

STILL UNSURE
- Baba reported the login hanging and needing a refresh before it let
  him in. Not reproduced here and not investigated — it may be the
  accounts round trip being slow, or a rerun that does not fire. Worth
  watching; if it happens again, note whether the spinner was moving.

FOR BABA
- ADMIN_USER = "admin" in the Streamlit Cloud secrets. That alone brings
  the admin tabs back.
- Then, unchanged: deploy the AUTH script, add AUTH_ADMIN_TOKEN, and
  create accounts for Emina and Marinko — the users tab still has only
  `admin` in it.
