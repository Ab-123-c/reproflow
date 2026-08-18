# normalize_username crashes on Unicode usernames

Calling `normalize_username()` with Chinese usernames raises an exception.

Expected: return a normalized username.
Actual: the call fails with a Unicode-related error.
