import json
import uuid

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest

from app import mongo

reminder_bp = Blueprint("reminder", __name__)
# Access the MongoDB reminders collection
reminders_collection = mongo.db.reminders
user_collection = mongo.db.users


def generate_reminder_id():
    """Generate a unique reminder ID using UUID."""
    unique_id = uuid.uuid4().hex[:8]  # Create a unique ID
    return f"{unique_id.upper()}"  # Return the ID in uppercase


def get_json_data(request):
    """Function to safely extract JSON data from the request."""
    try:
        return request.json
    except (BadRequest, json.JSONDecodeError):
        return None


def get_reminders(user_id):
    """Function to get reminders for a specific user."""
    # Query the database for reminders belonging to the user
    user_reminders = list(reminders_collection.find({"userId": user_id}))

    if not user_reminders:
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "No reminders for this user",
                    "reminders": [],
                }
            ),
            200,
        )

    # Create a list of reminders to return
    reminder_list = [
        {
            "_id": str(r["_id"]),
            "title": r["title"],
            "description": r["description"],
            "date": r["date"],
            "time": r["time"],
            "status": r["status"],
            "urgent": r["urgent"],
            "important": r["important"],
            "remId": r["remId"],
        }
        for r in user_reminders
    ]

    return (
        jsonify(
            {
                "status": "success",
                "message": "Retrieved all reminders",
                "reminders": reminder_list,
            }
        ),
        200,
    )


def create_reminder(data):
    """Function to create a reminder"""
    required_feilds = ["title", "description", "date", "time", "status", "userId"]
    for field in required_feilds:
        if field not in data:
            return (
                jsonify({"status": "error", "message": f"Missing field: {field}"}),
                400,
            )

    title = data.get("title")
    description = data.get("description")
    date = data.get("date")
    time = data.get("time")
    status = data.get("status")
    user_id = data.get("userId")
    urgent = data.get("isUrgent")
    important = data.get("isImportant")

    rem_id = generate_reminder_id()

    new_reminder = {
        "title": title,
        "description": description,
        "date": date,
        "time": time,
        "status": status,
        "urgent": urgent,
        "important": important,
        "userId": user_id,
        "remId": rem_id,
    }
    return new_reminder


def update_reminder(reminder_id, update_data):
    """Helper function to update a reminder in the database."""
    # Remove keys with None values from the update data
    update_data = {k: v for k, v in update_data.items() if v is not None}

    if not update_data:
        return jsonify({"status": "error", "message": "No valid fields to update"}), 400

    # Attempt to update the reminder in the database
    result = reminders_collection.update_one(
        {"remId": reminder_id}, {"$set": update_data}
    )

    if result.matched_count == 0:
        return jsonify({"status": "error", "message": "Reminder not found"}), 404

    if result.modified_count == 0:
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Reminder found, but no changes were made",
                }
            ),
            200,
        )

    return (
        jsonify({"status": "success", "message": "Reminder updated successfully"}),
        200,
    )


def delete_reminder(reminder_id):
    """Helper function to delete a reminder from the database."""
    result = reminders_collection.delete_one({"remId": reminder_id})
    if result.deleted_count == 0:
        return jsonify({"status": "error", "message": "Reminder not found"}), 404
    return (
        jsonify({"status": "success", "message": "Reminder deleted successfully"}),
        200,
    )


@reminder_bp.route("/patient", methods=["GET"])
def patient_get_reminders():
    """Retrieve reminders for a specific patient."""
    try:
        patient_id = request.args.get("userId")

        if not patient_id:
            return (
                jsonify({"status": "error", "message": "Patient ID is required"}),
                400,
            )

        # Call the helper function to get the reminders
        return get_reminders(patient_id)
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to retrieve patient reminders. Please try again.",
                    "error": str(e),
                }
            ),
            500,
        )


@reminder_bp.route("/caregiver", methods=["GET"])
def caregiver_get_reminders():
    """Retrieve reminders for a caregiver's patient."""
    try:
        caregiver_id = request.args.get("CGId")
        patient_id = request.args.get("PATId")

        if not caregiver_id or not patient_id:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Caregiver ID and Patient ID are required",
                    }
                ),
                400,
            )

        # Ensure the caregiver and patient belong to the same family
        caregiver = user_collection.find_one({"userId": caregiver_id})
        patient = user_collection.find_one({"userId": patient_id})
        if (
            not caregiver
            or not patient
            or caregiver["family_id"] != patient["family_id"]
        ):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "You do not have permission to view this patient's reminders",
                    }
                ),
                403,
            )

        # Call the helper function to get the reminders
        return get_reminders(patient_id)

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to retrieve patient reminders. Please try again.",
                    "error": str(e),
                }
            ),
            500,
        )


@reminder_bp.route("/patient", methods=["POST"])
def patient_post_reminder():
    """Create a new reminder for a patient based on the request data."""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON data"}), 400

        # Use the function to create a reminder
        new_reminder = create_reminder(data)
        if isinstance(new_reminder, tuple):  # Check if the function returned an error
            return new_reminder

        # Insert the new reminder into the database
        reminders_collection.insert_one(new_reminder)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Reminder saved successfully for patient",
                }
            ),
            201,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to post patients reminders. Please try again",
                    "error": str(e),
                }
            ),
            500,
        )


@reminder_bp.route("/caregiver", methods=["POST"])
def caregiver_post_reminder():
    """Create a new reminder for a patient based on the request data."""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON data"}), 400

        caregiver_id = data.get("CGId")
        patient_id = data.get("PATId")

        if not caregiver_id or not patient_id:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Please provide Caregiver ID and Paitent ID!",
                    }
                ),
                400,
            )

        caregiver = user_collection.find_one({"userId": caregiver_id})
        patient = user_collection.find_one({"userId": patient_id})
        if caregiver["family_id"] != patient["family_id"]:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "You don not have the permission to handle reminders for this patient",
                    }
                ),
                400,
            )

        new_reminder = create_reminder(data)
        if isinstance(new_reminder, tuple):
            return new_reminder

        reminders_collection.insert_one(new_reminder)
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Reminder saved successfully for patient",
                }
            ),
            201,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to post patients reminders. Please try again",
                    "error": str(e),
                }
            ),
            500,
        )


@reminder_bp.route("/patient/<reminder_id>", methods=["PUT"])
def patient_update_reminder(reminder_id):
    """Allow a patient to update their own reminder."""
    try:
        data = request.json  # Get JSON data from the request
        # Extract the patient's userId from the request body
        patient_id = data.get("userId")

        if not patient_id:
            return (
                jsonify({"status": "error", "message": "Patient ID is required"}),
                400,
            )

        # Prepare data to update
        update_data = {
            "title": data.get("title"),
            "description": data.get("description"),
            "date": data.get("date"),
            "time": data.get("time"),
            "status": data.get("status"),
            "urgent": data.get("isUrgent"),
            "important": data.get("isImportant"),
        }

        # Ensure the reminder belongs to the patient
        reminder = reminders_collection.find_one(
            {"remId": reminder_id, "userId": patient_id}
        )
        if not reminder:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Reminder not found or access denied",
                    }
                ),
                404,
            )

        # Call the helper function to update the reminder
        return update_reminder(reminder_id, update_data)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@reminder_bp.route("/caregiver/<reminder_id>", methods=["PUT"])
def caregiver_update_reminder(reminder_id):
    """Allow a caregiver to update a reminder for a patient."""
    try:
        data = request.json  # Get JSON data from the request

        # Extract caregiverId and patientId from the request body
        caregiver_id = data.get("CGId")
        patient_id = data.get("PATId")

        if not caregiver_id or not patient_id:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Caregiver ID and Patient ID are required",
                    }
                ),
                400,
            )

        # Prepare data to update
        update_data = {
            "title": data.get("title"),
            "description": data.get("description"),
            "date": data.get("date"),
            "time": data.get("time"),
            "status": data.get("status"),
            "urgent": data.get("isUrgent"),
            "important": data.get("isImportant"),
        }

        # Ensure the caregiver and patient belong to the same family
        caregiver = user_collection.find_one({"userId": caregiver_id})
        patient = user_collection.find_one({"userId": patient_id})
        if (
            not caregiver
            or not patient
            or caregiver["family_id"] != patient["family_id"]
        ):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "You do not have permission to update this reminder",
                    }
                ),
                403,
            )

        # Ensure the reminder belongs to the patient
        reminder = reminders_collection.find_one(
            {"remId": reminder_id, "userId": patient_id}
        )
        if not reminder:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Reminder not found or access denied",
                    }
                ),
                404,
            )

        # Call the helper function to update the reminder
        return update_reminder(reminder_id, update_data)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@reminder_bp.route("/patient/<user_id>/<rem_id>", methods=["DELETE"])
def patient_delete_reminder(user_id, rem_id):
    """Allow a patient to delete their own reminder."""
    try:
        if not user_id:
            return (
                jsonify({"status": "error", "message": "Patient ID is required"}),
                400,
            )

        # Ensure the reminder belongs to the patient
        reminder = reminders_collection.find_one({"remId": rem_id, "userId": user_id})
        if not reminder:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Reminder not found or access denied",
                    }
                ),
                404,
            )

        # Call the helper function to delete the reminder
        return delete_reminder(rem_id)

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to delete patient reminder. Please try again.",
                    "error": str(e),
                }
            ),
            500,
        )


@reminder_bp.route(
    "/caregiver/<caregiver_id>/<patient_id>/<rem_id>", methods=["DELETE"]
)
def caregiver_delete_reminder(caregiver_id, patient_id, rem_id):
    """Allow a caregiver to delete a reminder for a patient."""
    try:
        if not caregiver_id or not patient_id:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Caregiver ID and Patient ID are required",
                    }
                ),
                400,
            )

        # Ensure the caregiver and patient belong to the same family
        caregiver = user_collection.find_one({"userId": caregiver_id})
        patient = user_collection.find_one({"userId": patient_id})
        if (
            not caregiver
            or not patient
            or caregiver["family_id"] != patient["family_id"]
        ):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "You do not have permission to delete this reminder",
                    }
                ),
                403,
            )

        # Ensure the reminder belongs to the patient
        reminder = reminders_collection.find_one(
            {"remId": rem_id, "userId": patient_id}
        )
        if not reminder:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Reminder not found or access denied",
                    }
                ),
                404,
            )

        # Call the helper function to delete the reminder
        return delete_reminder(rem_id)

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to delete caregiver reminder. Please try again.",
                    "error": str(e),
                }
            ),
            500,
        )
