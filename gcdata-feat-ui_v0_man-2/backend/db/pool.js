const { Pool } = require('pg');

function createPool(dbConfig) {
  return new Pool(dbConfig);
}

module.exports = {
  createPool,
};
