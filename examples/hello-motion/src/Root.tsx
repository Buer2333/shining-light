import React from 'react';
import { Composition } from 'remotion';
import { HelloMotion } from './HelloMotion';

export const Root: React.FC = () => (
  <Composition id="HelloMotion" component={HelloMotion} width={1080} height={1080} fps={30} durationInFrames={120} />
);
