import os
from flask import (
    Flask, render_template, redirect,
    request, session, url_for, flash, abort
)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import json
if os.path.exists("env.py"):
    import env


app = Flask(__name__)


app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")


# global variables
mongo = PyMongo(app)


# home page
@app.route("/")
def home():
    recipes = mongo.db.recipes.find()
    return render_template("home.html", recipes=recipes)


# browse recipes
@app.route("/browse-recipes")
def browse_recipes():
    recipes = mongo.db.recipes.find()
    return render_template("browse-recipes.html", recipes=recipes)


# search recipes
@app.route("/search_recipe", methods=["GET", "POST"])
def search_recipe():
    category_select = request.form.get("category_select")
    ingredient_search = request.form.get("ingredient_search")

    # loop creating different search options
    if category_select == "all-types":
        if ingredient_search:
            # if all food types are selected and the text input is populated
            # search for the specific word
            recipe_search = list(mongo.db.recipes.find(
                {"$text": {"$search": ingredient_search}}))
        else:
            # search for everything if nothing is specified in the search
            recipe_search = mongo.db.recipes.find()
    elif category_select == "my_recipes":
        if ingredient_search:
            # search for user specific recipes and text search
            recipe_search = list(mongo.db.recipes.find(
                {"$and": [
                    {"created_by": session["user"]},
                    {"$text": {"$search": ingredient_search}}
                ]}
            ))
        else:
            # search only for user-specific recipes
            recipe_search = list(mongo.db.recipes.find(
                {"created_by": session["user"]}))
    else:
        if ingredient_search:
            # if both dropdown and input area are populated
            # search for both
            recipe_search = list(mongo.db.recipes.find(
                {"$and": [
                    {"food_category": category_select},
                    {"$text": {"$search": ingredient_search}}
                ]}
            ))
        else:
            # if only a food category is selected, search by that
            recipe_search = list(mongo.db.recipes.find(
                {"food_category": category_select}))

    return render_template("browse-recipes.html", recipes=recipe_search)


# my recipes menu option, searches for "my recipes" in browse-recipes
@app.route("/my_recipes", methods=["GET", "POST"])
def my_recipes():
    if "user" in session:
        recipe_search = list(mongo.db.recipes.find(
            {"created_by": session["user"]}))
        return render_template("browse-recipes.html", recipes=recipe_search)
    abort(403)


# view recipe
@app.route("/view-recipe/<recipe_id>")
def view_recipe(recipe_id):
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    if recipe:
        return render_template("view-recipe.html", recipe=recipe)
    abort(404)


# register
@app.route("/register", methods=["GET", "POST"])
def register():
    # TODO: change the redirect to an 403 error page
    if "user" in session:
        abort(403)

    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Name already taken!")
            return redirect(url_for("register"))

        user_data = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(user_data)

        session["user"] = request.form.get("username").lower()
        flash("Successfully Registered!")
        return redirect(url_for("home"))

    return render_template("register.html")


# log in
@app.route("/login", methods=["GET", "POST"])
def login():
    # TODO: change the redirect to an 403 error page
    if "user" in session:
        abort(403)

    if request.method == "POST":
        # if username exists in the database
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                # correct passord
                session["user"] = request.form.get("username").lower()
                return redirect(url_for("home"))
            else:
                # incorrect password
                flash("Incorrect password or username, try again!")
                return redirect(url_for("login"))
        else:
            # if username doesn't exist
            flash("Incorrect password or username, try again!")
            return redirect(url_for("login"))

    return render_template("login.html")


# log out
@app.route("/logout")
def logout():
    # TODO: change the redirect to an 403 error page
    if "user" in session:
        session.pop("user")
        flash("See you later!")

        return redirect(url_for("login"))

    abort(403)


# delete account
@app.route("/delete_account")
def delete_account():
    # TODO: change the redirect to an 403 error page
    if "user" in session:
        user_id = mongo.db.users.find_one({"username": session["user"]})["_id"]
        mongo.db.users.delete_one({"_id": ObjectId(user_id)})
        session.pop("user")
        flash("Sad to see you go, you can regster with us again at any time!!")

        return redirect(url_for("register"))

    abort(403)


# create recipe
@app.route("/create-recipe", methods=["GET", "POST"])
def create_recipe():
    # TODO: change the #redirect to an 403 error page
    if "user" in session:
        if request.method == "POST":
            recipe = json.loads(request.get_data(as_text=True))
            recipe["created_by"] = session["user"]
            mongo.db.recipes.insert_one(recipe)

        return render_template("create-recipe.html", recipe=0)

    abort(403)


# edit recipe
@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if "user" in session:
        recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
        if session["user"] == recipe["created_by"]:
            if request.method == "POST":
                recipe = json.loads(request.get_data(as_text=True))
                recipe["created_by"] = session["user"]
                mongo.db.recipes.update_one(
                    {"_id": ObjectId(recipe_id)}, {"$set": recipe})
                flash("Recipe successfully updated")
                recipes = mongo.db.recipes.find()
                return render_template("home.html", recipes=recipes)

            return render_template("create-recipe.html", recipe=recipe)

    abort(403)


# delete recipe
@app.route("/delete_recipe/<recipe_id>", methods=["GET", "POST"])
def delete_recipe(recipe_id):
    if "user" in session:
        recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
        if session["user"] == recipe.created_by:
            mongo.db.recipes.delete_one({"_id": ObjectId(recipe_id)})

            return redirect(url_for("home"))

    abort(403)


# error functions below

@app.errorhandler(403)
def page_forbidden(e):
    return render_template("403.html"), 403


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)
