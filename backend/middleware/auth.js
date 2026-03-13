const { verifyAuthToken } = require('../auth/jwt');

const VALID_ROLES = new Set(['website_admin', 'client_admin', 'user']);

function extractBearerToken(authorizationHeader = '') {
  const [scheme, token] = authorizationHeader.split(' ');
  if (!scheme || !token || scheme.toLowerCase() !== 'bearer') {
    return null;
  }
  return token;
}

function requireAuth(req, res, next) {
  try {
    const token = extractBearerToken(req.headers.authorization);
    if (!token) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const claims = verifyAuthToken(token);
    if (!VALID_ROLES.has(claims.role)) {
      return res.status(401).json({ error: 'Invalid token role' });
    }

    if (claims.role === 'client_admin' && !claims.clientName) {
      return res.status(401).json({ error: 'Invalid token scope for client admin' });
    }

    if (claims.role === 'user' && !claims.userId) {
      return res.status(401).json({ error: 'Invalid token scope for user role' });
    }

    req.auth = {
      authUserId: claims.sub,
      username: claims.username,
      role: claims.role,
      clientName: claims.clientName || null,
      userId: claims.userId ? Number(claims.userId) : null,
    };

    return next();
  } catch (_error) {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

function requireRoles(roles) {
  const roleSet = new Set(roles);
  return (req, res, next) => {
    if (!req.auth || !roleSet.has(req.auth.role)) {
      return res.status(403).json({ error: 'Forbidden' });
    }
    return next();
  };
}

module.exports = {
  requireAuth,
  requireRoles,
};
