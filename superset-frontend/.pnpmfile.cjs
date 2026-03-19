function readPackage(pkg, context) {
  const forceLumaVersion = '8.5.21';
  const forceDeckVersion = '8.8.27';

  // Force luma.gl consistency
  if (pkg.dependencies && pkg.dependencies['@luma.gl/core']) {
    pkg.dependencies['@luma.gl/core'] = forceLumaVersion;
  }
  if (pkg.peerDependencies && pkg.peerDependencies['@luma.gl/core']) {
    pkg.peerDependencies['@luma.gl/core'] = forceLumaVersion;
  }

  // Force deck.gl consistency
  if (pkg.name.startsWith('@deck.gl/')) {
    // Some internal deck packages need to be forced to the same minor version
    if (pkg.dependencies && pkg.dependencies['@deck.gl/core']) {
      pkg.dependencies['@deck.gl/core'] = forceDeckVersion;
    }
  }

  return pkg;
}

module.exports = {
  hooks: {
    readPackage,
  },
};
