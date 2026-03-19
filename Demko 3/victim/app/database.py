import sqlite3
from typing import Any, Dict, List, Optional

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e: Optional[Exception] = None) -> None:
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = sqlite3.connect(current_app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    db.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            title    TEXT NOT NULL,
            content  TEXT NOT NULL,
            author   TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()

    if db.execute('SELECT COUNT(*) FROM posts').fetchone()[0] == 0:
        _seed_posts(db)

    db.close()


def _seed_posts(db: sqlite3.Connection) -> None:
    posts = [
        (
            'Understanding Python Decorators',
            '''Decorators are one of Python's most powerful and elegant features. At their core, a decorator is simply a function that takes another function as an argument and returns a modified version of it.

The most common use case you'll encounter is the <code>@property</code> decorator, but they go much deeper than that. Consider a simple timing decorator:

<pre><code>def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"Elapsed: {time.time() - start:.2f}s")
        return result
    return wrapper

@timer
def slow_function():
    time.sleep(1)</code></pre>

This pattern is used extensively in frameworks like Flask itself — every <code>@app.route()</code> you write is a decorator registering your view function with the URL dispatcher.

The key insight is that decorators are just syntactic sugar. <code>@timer</code> above is exactly equivalent to writing <code>slow_function = timer(slow_function)</code> after the function definition. Once that clicks, the whole decorator ecosystem opens up.

Advanced usage includes parameterized decorators, class-based decorators, and stacking multiple decorators. The <code>functools.wraps</code> utility is essential when writing decorators — it preserves the original function's metadata so debugging stays sane.''',
            'Alice Nowak',
        ),
        (
            'Docker Best Practices for Production',
            '''After running Docker in production for several years, a few lessons stand out as non-negotiable.

<strong>Use multi-stage builds.</strong> Your final image should contain only what's needed to run the application — not your build toolchain, test dependencies, or source code. A typical Python service drops from 800MB to under 120MB with this alone.

<pre><code>FROM python:3.11 AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY . /app
WORKDIR /app</code></pre>

<strong>Pin your base image digests.</strong> <code>python:3.11-slim</code> is a moving target. In a reproducible build pipeline, use the full digest hash.

<strong>Run as a non-root user.</strong> Add <code>USER 1000</code> before your CMD. If your container is compromised, an attacker should not get root on the host via a container escape.

<strong>Health checks matter.</strong> Orchestrators like Kubernetes and Compose rely on health checks to know when your service is actually ready. An HTTP health endpoint on <code>/health</code> returning 200 is the minimum.

<strong>Treat logs as streams.</strong> Write to stdout/stderr, let the container runtime handle log rotation and shipping. Never write logs to files inside the container.''',
            'Marek Wiśniewski',
        ),
        (
            'REST API Design: Lessons from the Trenches',
            '''Designing a REST API that developers actually enjoy using is harder than it looks. Here are the principles I keep coming back to.

<strong>Resources, not actions.</strong> Your URLs should be nouns, not verbs. <code>POST /posts</code> creates a post. <code>DELETE /posts/42</code> removes it. If you find yourself writing <code>/getPosts</code> or <code>/deleteUser</code>, stop and reconsider.

<strong>Consistent error shapes.</strong> Every error response should have the same JSON structure — at minimum a <code>code</code> and a human-readable <code>message</code>. Clients shouldn't need to handle five different error formats.

<pre><code>{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Title must not be empty",
    "field": "title"
  }
}</code></pre>

<strong>Version from day one.</strong> Put <code>/v1/</code> in your URL prefix even if you think you'll never need v2. You will. Breaking changes happen, and deprecating a versioned API is painless compared to migrating everyone off an unversioned one.

<strong>Return 422 for validation errors, not 400.</strong> HTTP 400 means the request was malformed (bad JSON, missing Content-Type). HTTP 422 means the request was well-formed but semantically invalid. Most APIs get this wrong.

<strong>Pagination is not optional.</strong> Any collection endpoint that could return more than ~50 items needs cursor-based or offset pagination. Returning unbounded lists will eventually take down your service.''',
            'Alice Nowak',
        ),
        (
            'Git Internals: What Actually Happens on git commit',
            '''Most developers use Git daily without knowing what actually happens when they run <code>git commit</code>. Understanding the internals makes you dramatically better at resolving conflicts, recovering lost work, and understanding rebase.

Git stores four types of objects, all content-addressed by their SHA-1 hash:

<ul>
<li><strong>blob</strong> — raw file contents</li>
<li><strong>tree</strong> — a directory listing (maps names to blobs/trees)</li>
<li><strong>commit</strong> — points to a tree, has parent commit(s), author, message</li>
<li><strong>tag</strong> — annotated tag object</li>
</ul>

When you run <code>git commit</code>, Git:
1. Hashes each staged file into a blob object
2. Builds tree objects representing your directory structure
3. Creates a commit object pointing to the root tree and your previous commit
4. Updates the branch ref (e.g. <code>.git/refs/heads/main</code>) to the new commit hash

That's it. A branch is literally just a file containing a 40-character hash.

This is why <code>git reflog</code> can recover "lost" commits — the commit objects still exist in the object store until garbage collection runs. If you've ever done a <code>git reset --hard</code> and panicked, check <code>git reflog</code> immediately.''',
            'Tomasz Kowalski',
        ),
    ]
    db.executemany(
        'INSERT INTO posts (title, content, author) VALUES (?, ?, ?)',
        posts,
    )
    db.commit()


def get_posts() -> List[Dict[str, Any]]:
    rows = get_db().execute(
        'SELECT * FROM posts ORDER BY created_at DESC'
    ).fetchall()
    return [dict(row) for row in rows]


def get_post(post_id: int) -> Optional[Dict[str, Any]]:
    row = get_db().execute(
        'SELECT * FROM posts WHERE id = ?', (post_id,)
    ).fetchone()
    return dict(row) if row else None


def create_post(title: str, content: str, author: str) -> int:
    db = get_db()
    cursor = db.execute(
        'INSERT INTO posts (title, content, author) VALUES (?, ?, ?)',
        (title, content, author),
    )
    db.commit()
    return cursor.lastrowid
