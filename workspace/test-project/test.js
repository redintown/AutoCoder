const { createTodo } = require("./src/app");

const todo = createTodo("  Buy groceries  ");

if (todo.title !== "Buy groceries") {
    throw new Error("Todo title should be trimmed");
}

if (todo.completed !== false) {
    throw new Error("Todo should initially be incomplete");
}

let errorThrown = false;

try {
    createTodo("   ");
} catch (error) {
    errorThrown = true;
}

if (!errorThrown) {
    throw new Error("Whitespace-only title should throw an error");
}

console.log("All tests passed.");