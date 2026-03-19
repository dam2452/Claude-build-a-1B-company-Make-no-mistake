import os
import time
from typing import Generator, Union

from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    render_template_string,
    request,
    stream_with_context,
    url_for,
)

from .database import create_post, get_post, get_posts

bp = Blueprint('blog', __name__)


@bp.route('/')
def index() -> Union[str, Response]:
    return render_template('index.html', posts=get_posts())


@bp.route('/post/<int:post_id>')
def post(post_id: int) -> Union[str, Response]:
    p = get_post(post_id)
    if p is None:
        return render_template('404.html'), 404
    return render_template('post.html', post=p)


@bp.route('/write', methods=['GET', 'POST'])
def write() -> Union[str, Response]:
    if request.method == 'POST':
        if request.form.get('action') == 'preview':
            return redirect(url_for('blog.preview'), code=307)
        create_post(
            title=request.form['title'],
            content=request.form['content'],
            author=request.form['author'],
        )
        return redirect(url_for('blog.index'))
    return render_template('write.html')


@bp.route('/stream')
def stream() -> Response:
    template_path = os.path.join(
        current_app.root_path, current_app.template_folder, 'index.html'
    )

    @stream_with_context
    def _generate() -> Generator[str, None, None]:
        baseline = os.path.getmtime(template_path)
        yield 'data: ok\n\n'
        while True:
            time.sleep(1)
            if os.path.getmtime(template_path) != baseline:
                yield 'event: reload\ndata: now\n\n'
                return

    return Response(_generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@bp.route('/preview', methods=['POST'])
def preview() -> str:
    title = request.form.get('title', '')
    content = request.form.get('content', '')
    # Renders user-provided Jinja2 template for live post preview
    rendered = render_template_string(content)
    return render_template('preview.html', title=title, content=rendered)
