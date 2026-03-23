function readPackage(pkg, context) {
  const LUMA_VERSION = '8.5.21';
  const DECK_VERSION = '8.8.27';

  const fix = deps => {
    if (!deps) return;
    Object.keys(deps).forEach(name => {
      // Force all @luma.gl packages to v8
      if (name.startsWith('@luma.gl/')) {
        deps[name] = LUMA_VERSION;
      }
      // Force all @deck.gl packages to v8
      if (name.startsWith('@deck.gl/') || name === 'deck.gl') {
        deps[name] = DECK_VERSION;
      }
    });
  };

  // Fix all dependency types for every package processed
  fix(pkg.dependencies);
  fix(pkg.devDependencies);
  fix(pkg.peerDependencies);

  return pkg;
}

module.exports = {
  hooks: {
    readPackage,
  },
};
