import Svg, { Path, Circle, Rect, G, Defs, LinearGradient, Stop } from 'react-native-svg';
import { colors } from '@/lib/theme';

type Props = { size?: number };

/**
 * Illustration: A tidy mailbox with a checkmark — inbox is all clear.
 */
export function InboxClearIllustration({ size = 140 }: Props) {
  const s = size / 140;
  return (
    <Svg width={size} height={size} viewBox="0 0 140 140" fill="none">
      <Defs>
        <LinearGradient id="bgGrad" x1="70" y1="10" x2="70" y2="130" gradientUnits="userSpaceOnUse">
          <Stop offset="0" stopColor={colors.primary[100]} stopOpacity={0.5} />
          <Stop offset="1" stopColor={colors.primary[50]} stopOpacity={0.2} />
        </LinearGradient>
        <LinearGradient id="envGrad" x1="70" y1="40" x2="70" y2="100" gradientUnits="userSpaceOnUse">
          <Stop offset="0" stopColor={colors.primary[200]} />
          <Stop offset="1" stopColor={colors.primary[100]} />
        </LinearGradient>
      </Defs>

      {/* Background circle */}
      <Circle cx="70" cy="70" r="58" fill="url(#bgGrad)" />

      {/* Envelope body */}
      <Rect x="32" y="52" width="76" height="50" rx="6" fill="url(#envGrad)" stroke={colors.primary[400]} strokeWidth="1.5" />

      {/* Envelope flap */}
      <Path
        d="M32 58L70 80L108 58"
        stroke={colors.primary[400]}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <Path
        d="M32 52L70 74L108 52"
        fill={colors.primary[50]}
        stroke={colors.primary[400]}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Checkmark circle */}
      <Circle cx="96" cy="46" r="16" fill={colors.success[500]} />
      <Path
        d="M88 46L93 51L104 41"
        stroke={colors.white}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />

      {/* Decorative dots */}
      <Circle cx="26" cy="44" r="2.5" fill={colors.primary[200]} opacity={0.6} />
      <Circle cx="118" cy="88" r="2" fill={colors.primary[200]} opacity={0.5} />
      <Circle cx="22" cy="92" r="1.5" fill={colors.primary[200]} opacity={0.4} />
    </Svg>
  );
}
