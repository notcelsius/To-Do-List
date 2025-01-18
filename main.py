from flask import Flask, render_template, request, redirect, url_for, jsonify   # framework to create web app
from flask_sqlalchemy import SQLAlchemy # SQLAlchemy handles interactions w/ database, is also object relational mapper connecting Flask app to the database
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column   # defines models (like Task) and maps Python objects to database table, allowing operations to be performed without writing raw SQL
from sqlalchemy import String, DateTime, Boolean    # data types for structure of the database table
from datetime import datetime   # for getting the date
from flask_bootstrap import Bootstrap5  # for styling

# Initialization of app and database
app = Flask(__name__)   # initiliazes app
Bootstrap5(app)         # adds bootstrap to app for styling

class Base(DeclarativeBase):    # base class for SQLAlchemy models
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///todolist.db" # configures database connection
db = SQLAlchemy(model_class=Base)   # initializes SQLAlchemy object with Base as model class
db.init_app(app)    # connects db to Flask app

# each new instance of Task is a new row
class Task(db.Model):   # defines a model called Task that represents a table in the db
    # all columns for task
    name: Mapped[str] = mapped_column(String(250), nullable=False, primary_key=True)
    do_by: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    complete: Mapped[bool] = mapped_column(Boolean, default=False)  

    # converts the model into a dictionary
    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

with app.app_context(): # sets up app context for Flask app
    db.create_all() # creates all tables defined in model

# Routing Stuff
# home route
@app.route('/')
def home():
    result = db.session.execute(db.select(Task).order_by(Task.do_by))   # executes query that selects all Tasks and orders them by do_by date
    all_tasks = result.scalars().all()  # extract all column values for the Task instances
    return render_template("index.html", tasks=all_tasks) # renders the index.html template and passes all_tasks list to the template

# add route
@app.route('/add', methods=["GET", "POST"]) # accepts both GET and POST requests
def add():
    if request.method == "POST":
        # get the name and do_by using request to access the submitted form
        name = request.form["name"]
        do_by_str = request.form["do_by"]
        
        
        do_by = datetime.strptime(do_by_str, "%Y-%m-%dT%H:%M")  # convert the string to a datetime object
        
        # creates new task with the name and do_by
        new_task = Task(
            name=name,
            do_by=do_by
        )
        db.session.add(new_task)    # add new task to the db
        db.session.commit()         # save the changes
        return redirect(url_for('home'))    # return to home page
    return render_template("add.html")  # if it was a GET request, then send them to the add.html form

# edit route
@app.route("/edit/<task_name>", methods=["GET", "POST"])    # accepts both GET and POST requests
def edit(task_name):
    task_to_update = db.get_or_404(Task, task_name) # retrieves the Task object with given task_name

    if request.method == "POST":
        # update task details using the task's primary key (name)
        task_to_update.do_by = datetime.strptime(request.form["do_by"], "%Y-%m-%dT%H:%M")
        task_to_update.name = request.form["name"]

        db.session.commit() # save changes
        return redirect(url_for('home'))    # return to home
    return render_template("edit.html", task=task_to_update) # render the edit page with the current task details

# delete route
@app.route('/delete')
def delete():
    task_name = request.args.get('task_name')   # retrieves task_name from query string in the url
    task_to_delete = db.get_or_404(Task, task_name) # retrieves the Task object with given task_name
    db.session.delete(task_to_delete)   # delete task
    db.session.commit() # save changes
    return redirect(url_for('home'))    # return to homepage

# delete all route
@app.route('/delete_all', methods=['POST']) # use POST request to prevent accidental triggering
def delete_all():
    try:
        db.session.query(Task).delete() # deletes all rows from Task table
        db.session.commit()         # save changes
        return redirect(url_for('home'))    # return to home page
    except Exception as e:
        db.session.rollback()   # prevents partial deletions
        return str(e), 500

# mark complete route
@app.route('/mark_complete/<task_name>', methods=['POST'])  # accepts POST requests
def mark_complete(task_name):
    task = db.get_or_404(Task, task_name)   # get the task
    if task:
        task.complete = not task.complete  # toggle the 'complete' status
        db.session.commit()
    return redirect(url_for('home'))  # redirect back to the todo list

# API stuff
# route for getting all tasks
@app.route('/all', methods=["GET"])
def get_all_tasks():
    result = db.session.execute(db.select(Task).order_by(Task.name))   # executes query to select all tasks ordered by name
    all_tasks = result.scalars().all()  # retrieves all tasks as plain python objects
    return jsonify(tasks=[task.to_dict() for task in all_tasks]), 200  # returns tasks as json

# route for searching tasks by name
@app.route('/search', methods=["GET"])
def get_task_by_name():
    query_name = request.args.get("name")  # retrieves the 'name' query parameter from the request
    result = db.session.execute(db.select(Task).where(Task.name == query_name))  # query tasks by name
    all_tasks = result.scalars().all()  # retrieves all matching tasks
    if all_tasks:
        return jsonify(tasks=[task.to_dict() for task in all_tasks]), 200  # returns matching tasks as json
    else:
        return jsonify(error={"not found"}), 404  # if no tasks match, returns an error with 404 status

# route for creating a new task
@app.route('/create', methods=["POST"])
def create_task():
    # retrieve data from the form
    name = request.form.get("name")  # retrieves task name from the form
    do_by_str = request.form.get("do_by")  # retrieves the 'do_by' date from the form

    # debugging: print the received 'do_by' value
    print(f"received 'do_by': {do_by_str}")

    # convert the 'do_by' string into a datetime object
    do_by = datetime.strptime(do_by_str, "%Y-%m-%dT%H:%M")

    # create a new task object
    new_task = Task(
        name=name,
        do_by=do_by,
        complete=False  # new tasks are not completed by default
    )

    # add the new task to the database
    db.session.add(new_task)
    db.session.commit()

    return jsonify(response={"success": "successfully added the new task."}), 200  # return success response

# route for editing the task name
@app.route("/edit-name/<task_name>", methods=["PATCH"])
def edit_name(task_name):
    # retrieve the task by name
    task_to_update = db.get_or_404(Task, task_name)  # fetches the task with the provided name

    # get the new name from the query parameter
    new_name = request.args.get("new_name")  # retrieve the new name to update

    # update the task's name
    task_to_update.name = new_name

    # commit the changes to the database
    db.session.commit()

    # return success message with updated task
    return jsonify(response={"success": "successfully changed the task name."})

# route for editing the 'do_by' date of a task
@app.route("/edit-do-by/<task_name>", methods=["PATCH"])
def edit_do_by(task_name):
    # retrieve the task by name
    task_to_update = db.get_or_404(Task, task_name)

    # get the new 'do_by' value from the query parameter
    new_do_by = request.args.get("new_do_by")

    # check if new_do_by is provided
    if not new_do_by:
        return jsonify(error={"missing data": "'new_do_by' is required."}), 400  # return error if 'new_do_by' is missing

    try:
        # convert the new 'do_by' string to a datetime object
        task_to_update.do_by = datetime.strptime(new_do_by, "%Y-%m-%dT%H:%M")
    except ValueError:
        return jsonify(error={"invalid date format": "please use the format 'yyyy-mm-ddThh:mm'."}), 400  # return error for invalid format

    # commit the changes to the database
    db.session.commit()

    # return success message with updated task
    return jsonify(response={"success": "successfully changed the task do by."})

# route for editing the completion status of a task
@app.route("/edit-completion/<task_name>", methods=["PATCH"])
def edit_completion(task_name):
    # retrieve the task by name
    task_to_update = db.get_or_404(Task, task_name)

    # get the new completion status from the query parameter
    new_completion = request.args.get("new_completion")

    # check if new_completion is provided
    if not new_completion:
        return jsonify(error={"missing data": "'new_completion' is required."}), 400  # return error if 'new_completion' is missing

    # check if the new completion value is valid (true/false)
    if new_completion.lower() not in ["true", "false"]:
        return jsonify(error={"invalid value": "'new_completion' should be 'true' or 'false'."}), 400  # return error for invalid value

    # update the task's completion status
    task_to_update.complete = new_completion.lower() == "true"

    # commit the changes to the database
    db.session.commit()

    # return success message with updated task
    return jsonify(response={"success": "successfully changed the task completion."}), 200

# route for deleting a specific task by name
@app.route("/delete-task/<task_name>", methods=["DELETE"])
def delete_task(task_name):
    # retrieve the task by name
    task_to_delete = db.get_or_404(Task, task_name)

    # delete the task
    db.session.delete(task_to_delete)
    db.session.commit()

    # return a success message after deletion
    return jsonify(response={"success": "successfully deleted the task"}), 200

# route for clearing all tasks (deleting them)
@app.route('/clear', methods=['POST'])
def api_delete_all():
    try:
        db.session.query(Task).delete()  # deletes all tasks from the task table
        db.session.commit()  # commit the deletion
        return {"message": "all tasks successfully deleted.", "status": "success"}, 200  # return success message
    except Exception as e:
        db.session.rollback()  # rollback the transaction if there is an error
        return {"message": f"an error occurred: {str(e)}", "status": "error"}, 500  # return error message in case of failure

if __name__ == "__main__":
    app.run(debug=True)