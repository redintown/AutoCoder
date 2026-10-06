function createTodo(title) {
    if (!title || !title.trim()) {
        throw new Error('Todo title cannot be empty');
    }

    title = title.trim();

    return {
        title: title,
        completed: false
    };
}

module.exports = { createTodo };
