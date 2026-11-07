import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { Dust, GrayLines, Seal, easeInOut, easeOut, lerp, rectToQuad } from '@shining-motion/kit';

const CARD = { w: 560, h: 360 };
const FLAT: [number, number][] = [[260, 360], [820, 360], [820, 720], [260, 720]];
const TILTED: [number, number][] = [[300, 300], [860, 390], [800, 760], [220, 640]];

// One card stays on screen and changes state, instead of cutting between slides.
export const HelloMotion: React.FC = () => {
  const frame = useCurrentFrame();
  const tilt = easeInOut(frame, 54, 30);
  const quad = FLAT.map(([x, y], i) => [lerp(x, TILTED[i][0], tilt), lerp(y, TILTED[i][1], tilt)] as [number, number]);

  return (
    <AbsoluteFill style={{ background: '#11131A', fontFamily: 'Helvetica, Arial, sans-serif' }}>
      <Dust w={1080} h={1080} n={260} f={frame} />
      <div style={{ position: 'absolute', left: 0, top: 0, width: CARD.w, height: CARD.h, background: '#F5F1E8', transformOrigin: '0 0', transform: rectToQuad(CARD.w, CARD.h, quad) }}>
        <div style={{ padding: 44 }}>
          <GrayLines n={6} w={CARD.w - 88} prog={easeOut(frame, 8, 36)} h={14} gap={20} color="#B9B4A8" />
        </div>
        <div style={{ position: 'absolute', right: 40, bottom: 34 }}>
          <Seal text="DONE" at={36} px={64} color="#D6452B" />
        </div>
      </div>
    </AbsoluteFill>
  );
};
