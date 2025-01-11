from flask import Flask, render_template, request, redirect, url_for, jsonify
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

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}



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

@app.route('/delete_all', methods=['POST'])
def delete_all():
    try:
        db.session.query(Task).delete()
        db.session.commit()
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        return str(e), 500



@app.route('/mark_complete/<task_name>', methods=['POST'])
def mark_complete(task_name):
    task = Task.query.filter_by(name=task_name).first()
    if task:
        task.complete = not task.complete  # Toggle the 'complete' status
        db.session.commit()
    return redirect(url_for('home'))  # Redirect back to the todo list


# API stuff

@app.route('/all', methods=["GET"])
def get_all_tasks():
    result = db.session.execute(db.select(Task).order_by(Task.name))
    all_tasks = result.scalars().all()
    return jsonify(tasks=[task.to_dict() for task in all_tasks]), 200

@app.route('/search', methods=["GET"])
def get_task_by_name():
    query_name = request.args.get("name")
    result = db.session.execute(db.select(Task).where(Task.name == query_name))
    all_tasks = result.scalars().all()
    if all_tasks:
        return jsonify(tasks=[task.to_dict() for task in all_tasks]), 200
    else:
        return jsonify(error={"Not Found"}), 404
    
@app.route('/create', methods=["POST"])
def create_task():
    # Retrieve data from the form
    name = request.form.get("name")
    do_by_str = request.form.get("do_by")  # Get the string from the form

    # Debugging: Print the received 'do_by' value
    print(f"Received 'do_by': {do_by_str}")

    do_by = datetime.strptime(do_by_str, "%Y-%m-%dT%H:%M")

    # Create a new Task object
    new_task = Task(
        name=name,
        do_by=do_by,
        complete=False  # New tasks are not completed by default
    )

    # Add the new task to the database
    db.session.add(new_task)
    db.session.commit()

    return jsonify(response={"success": "Successfully added the new task."}), 200

@app.route("/edit-name/<task_name>", methods=["PATCH"])
def edit_name(task_name):
    # Retrieve the task by name
    task_to_update = db.get_or_404(Task, task_name)

    # Get the new name from the query parameter
    new_name = request.args.get("new_name")

    # Update the task's name
    task_to_update.name = new_name

    # Commit the changes to the database
    db.session.commit()

    # Return the updated task details
    return jsonify(response={"success": "Successfully changed the task name."})


@app.route("/edit-do-by/<task_name>", methods=["PATCH"])
def edit_do_by(task_name):
    # Retrieve the task by name
    task_to_update = db.get_or_404(Task, task_name)

    # Get the new do_by value from the query parameter
    new_do_by = request.args.get("new_do_by")

    # Check if new_do_by is provided
    if not new_do_by:
        return jsonify(error={"Missing Data": "'new_do_by' is required."}), 400

    try:
        # Convert the new do_by string to a datetime object
        task_to_update.do_by = datetime.strptime(new_do_by, "%Y-%m-%dT%H:%M")
    except ValueError:
        return jsonify(error={"Invalid Date Format": "Please use the format 'YYYY-MM-DDTHH:MM'."}), 400

    # Commit the changes to the database
    db.session.commit()

    # Return the updated task details
    return jsonify(response={"success": "Successfully changed the task do by."})


@app.route("/edit-completion/<task_name>", methods=["PATCH"])
def edit_completion(task_name):
    # Retrieve the task by name
    task_to_update = db.get_or_404(Task, task_name)

    # Get the new completion status from the query parameter
    new_completion = request.args.get("new_completion")

    # Check if new_completion is provided
    if not new_completion:
        return jsonify(error={"Missing Data": "'new_completion' is required."}), 400

    # Check if the new completion value is valid
    if new_completion.lower() not in ["true", "false"]:
        return jsonify(error={"Invalid Value": "'new_completion' should be 'true' or 'false'."}), 400

    # Update the task's completion status
    task_to_update.complete = new_completion.lower() == "true"

    # Commit the changes to the database
    db.session.commit()

    # Return the updated task details
    return jsonify(response={"success": "Successfully changed the task completion."}), 200

@app.route("/delete-task/<task_name>", methods=["DELETE"])
def delete_task(task_name):
    # Retrieve the task by name
    task_to_delete = db.get_or_404(Task, task_name)

    # Delete the task
    db.session.delete(task_to_delete)
    db.session.commit()

    # Return a success message
    return jsonify(response={"success": "Successfully deleted the task"}), 200

@app.route('/clear', methods=['POST'])
def api_delete_all():
    try:
        db.session.query(Task).delete()
        db.session.commit()
        return {"message": "All tasks successfully deleted.", "status": "success"}, 200
    except Exception as e:
        db.session.rollback()
        return {"message": f"An error occurred: {str(e)}", "status": "error"}, 500






if __name__ == "__main__":
    app.run(debug=True)