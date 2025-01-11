from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean
from datetime import datetime
from flask_bootstrap import Bootstrap5

app = Flask(__name__)
Bootstrap5(app)

class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///todolist.db"
db = SQLAlchemy(model_class=Base)
db.init_app(app)

class Task(db.Model):
    name: Mapped[str] = mapped_column(String(250), nullable=False, primary_key=True)
    do_by: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    complete: Mapped[bool] = mapped_column(Boolean, default=False)  # New field for completion status



with app.app_context():
    db.create_all()

@app.route('/')
def home():
    result = db.session.execute(db.select(Task).order_by(Task.do_by))
    all_tasks = result.scalars().all()
    return render_template("index.html", tasks=all_tasks)

@app.route('/add', methods=["GET", "POST"])
def add():
    if request.method == "POST":
        name = request.form["name"]
        do_by_str = request.form["do_by"]  # Get the string from the form
        
        # Convert the string to a datetime object
        do_by = datetime.strptime(do_by_str, "%Y-%m-%dT%H:%M")
        
        new_task = Task(
            name=name,
            do_by=do_by  # Update to match the new variable name
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("add.html")


@app.route("/edit/<task_name>", methods=["GET", "POST"])
def edit(task_name):
    task_to_update = db.get_or_404(Task, task_name)

    if request.method == "POST":
        # Update task details using the task's primary key (name)
        task_to_update.do_by = datetime.strptime(request.form["do_by"], "%Y-%m-%dT%H:%M")
        task_to_update.name = request.form["name"]

        db.session.commit()
        return redirect(url_for('home'))

    # Render the edit page with the current task details
    return render_template("edit.html", task=task_to_update)

@app.route('/delete')
def delete():
    task_name = request.args.get('task_name')
    task_to_delete = db.get_or_404(Task, task_name)
    db.session.delete(task_to_delete)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/mark_complete/<task_name>', methods=['POST'])
def mark_complete(task_name):
    task = Task.query.filter_by(name=task_name).first()
    if task:
        task.complete = not task.complete  # Toggle the 'complete' status
        db.session.commit()
    return redirect(url_for('home'))  # Redirect back to the todo list


if __name__ == "__main__":
    app.run(debug=True)