const array = Array.from({length: 1000}, (_, i) => ({ status: i % 4 === 0 ? "success" : i % 4 === 1 ? "failed" : i % 4 === 2 ? "partial" : "unknown" }));

console.time("multiple filter");
for (let j = 0; j < 1000; j++) {
  const success = array.filter(x => x.status === "success").length;
  const failed = array.filter(x => x.status === "failed").length;
  const partial = array.filter(x => x.status === "partial").length;
  const unknown = array.filter(x => x.status === "unknown").length;
}
console.timeEnd("multiple filter");

console.time("reduce");
for (let j = 0; j < 1000; j++) {
  const counts = array.reduce((acc, curr) => {
    acc[curr.status] = (acc[curr.status] || 0) + 1;
    return acc;
  }, {});
}
console.timeEnd("reduce");
