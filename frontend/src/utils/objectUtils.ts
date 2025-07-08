/**
 * Sets a property at a given path within an object, returning a new object.
 * Maintains immutability.
 *
 * @param obj The object to update.
 * @param path A dot-separated string representing the path to the property.
 * @param value The value to set at the specified path.
 * @returns A new object with the property set, or the original object if path is invalid.
 */
export const setPropertyByPath = <T extends Record<string, any>>(
  obj: T,
  path: string,
  value: any
): T => {
  const keys = path.split('.');

  // Helper function to recursively update the object
  const updateRecursively = (currentObj: any, currentIndex: number): any => {
    if (currentIndex === keys.length) {
      return value; // We've reached the target, set the value
    }

    const key = keys[currentIndex];

    // Ensure currentObj is an object or array before proceeding
    let newPart;
    if (Array.isArray(currentObj)) {
      newPart = [...currentObj]; // Clone array
    } else if (typeof currentObj === 'object' && currentObj !== null) {
      newPart = { ...currentObj }; // Clone object
    } else {
      // If path tries to traverse a non-object/array, create objects along the path
      // Determine if next key is a number (for array) or string (for object)
      const nextKeyIsNumber = currentIndex + 1 < keys.length && !isNaN(parseInt(keys[currentIndex + 1], 10));
      newPart = nextKeyIsNumber ? [] : {};
    }

    newPart[key] = updateRecursively(newPart[key], currentIndex + 1);
    return newPart;
  };

  return updateRecursively(obj, 0);
};

/**
 * Gets a property at a given path within an object.
 *
 * @param obj The object to query.
 * @param path A dot-separated string representing the path to the property.
 * @returns The value at the specified path, or undefined if path is invalid.
 */
export const getPropertyByPath = (obj: any, path: string): any => {
  const keys = path.split('.');
  let current = obj;
  for (const key of keys) {
    if (typeof current !== 'object' || current === null || !current.hasOwnProperty(key)) {
      return undefined;
    }
    current = current[key];
  }
  return current;
};

// Example Usage:
// const myObj = { a: { b: { c: 1 } }, d: [0, 1, { e: 2 }] };
// const updatedObj1 = setPropertyByPath(myObj, "a.b.c", 100);
// console.log(updatedObj1); // { a: { b: { c: 100 } }, d: [ 0, 1, { e: 2 } ] }
// console.log(myObj); // Original object is unchanged

// const updatedObj2 = setPropertyByPath(myObj, "a.b.x", 200); // New property
// console.log(updatedObj2); // { a: { b: { c: 1, x: 200 } }, d: [ 0, 1, { e: 2 } ] }

// const updatedObj3 = setPropertyByPath(myObj, "d.2.e", 300);
// console.log(updatedObj3); // { a: { b: { c: 1 } }, d: [ 0, 1, { e: 300 } ] }

// const val = getPropertyByPath(updatedObj3, "d.2.e");
// console.log(val); // 300
