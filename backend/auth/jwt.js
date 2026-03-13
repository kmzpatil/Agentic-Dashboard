const jwt = require('jsonwebtoken');

const DEFAULT_EXPIRY = process.env.JWT_EXPIRES_IN || '8h';

function getJwtSecret() {
  const secret = process.env.JWT_SECRET;
  if (!secret && process.env.NODE_ENV === 'production') {
    throw new Error('Missing required JWT_SECRET environment variable');
  }
  return secret || 'local-dev-jwt-secret-change-me';
}

function signAuthToken(payload) {
  return jwt.sign(payload, getJwtSecret(), { expiresIn: DEFAULT_EXPIRY });
}

function verifyAuthToken(token) {
  return jwt.verify(token, getJwtSecret());
}

module.exports = {
  signAuthToken,
  verifyAuthToken,
};
