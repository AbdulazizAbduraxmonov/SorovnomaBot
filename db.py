import mysql.connector


def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="Admin",
        password="Aa12345",
        database="Qbot"
    )
    return connection


def get_survey():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT text, image_url FROM survey ORDER BY id DESC LIMIT 1")
    result = cursor.fetchone()
    connection.close()
    return result if result else ("", "")


def set_survey(text, image_url):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO survey (text, image_url) VALUES (%s, %s)", (text, image_url))
    connection.commit()
    connection.close()


def get_candidates():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, name FROM candidates")
    results = cursor.fetchall()
    connection.close()
    return {str(row[0]): row[1] for row in results}


def add_candidate(name):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO candidates (name) VALUES (%s)", (name,))
    connection.commit()
    connection.close()


def update_candidate(candidate_id, name):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE candidates SET name = %s WHERE id = %s", (name, candidate_id))
    connection.commit()
    connection.close()


def delete_candidate(candidate_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Avval ushbu nomzodga berilgan barcha ovozlarni o'chiring
    cursor.execute("DELETE FROM votes WHERE candidate_id = %s", (candidate_id,))

    # Keyin nomzodni o'chiring
    cursor.execute("DELETE FROM candidates WHERE id = %s", (candidate_id,))

    connection.commit()
    connection.close()


def record_vote(user_id, candidate_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO votes (user_id, candidate_id) VALUES (%s, %s)", (user_id, candidate_id))
    connection.commit()
    connection.close()


def get_vote_count():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT candidate_id, COUNT(*) FROM votes GROUP BY candidate_id")
    results = cursor.fetchall()
    connection.close()
    return {str(row[0]): row[1] for row in results}
