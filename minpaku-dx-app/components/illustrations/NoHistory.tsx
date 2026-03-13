import Svg, { Path, Circle, Rect, G, Defs, LinearGradient, Stop } from 'react-native-svg';
import { colors } from '@/lib/theme';

type Props = { size?: number };

/**
 * Illustration: A clock with empty document pages — no history yet.
 */
export function NoHistoryIllustration({ size = 140 }: Props) {
  return (
    <Svg width={size} height={size} viewBox="0 0 140 140" fill="none">
      <Defs>
        <LinearGradient id="hBgGrad" x1="70" y1="10" x2="70" y2="130" gradientUnits="userSpaceOnUse">
          <Stop offset="0" stopColor={colors.gray[200]} stopOpacity={0.4} />
          <Stop offset="1" stopColor={colors.gray[100]} stopOpacity={0.15} />
        </LinearGradient>
        <LinearGradient id="pageGrad" x1="70" y1="30" x2="70" y2="110" gradientUnits="userSpaceOnUse">
          <Stop offset="0" stopColor={colors.white} />
          <Stop offset="1" stopColor={colors.gray[50]} />
        </LinearGradient>
      </Defs>

      {/* Background circle */}
      <Circle cx="70" cy="70" r="58" fill="url(#hBgGrad)" />

      {/* Back page */}
      <Rect x="46" y="34" width="52" height="66" rx="5" fill={colors.gray[200]} opacity={0.6} />

      {/* Front page */}
      <Rect x="38" y="40" width="52" height="66" rx="5" fill="url(#pageGrad)" stroke={colors.gray[300]} strokeWidth="1.2" />

      {/* Page lines */}
      <Rect x="48" y="54" width="32" height="3" rx="1.5" fill={colors.gray[200]} />
      <Rect x="48" y="63" width="24" height="3" rx="1.5" fill={colors.gray[200]} />
      <Rect x="48" y="72" width="28" height="3" rx="1.5" fill={colors.gray[200]} />
      <Rect x="48" y="81" width="18" height="3" rx="1.5" fill={colors.gray[200]} opacity={0.6} />

      {/* Clock */}
      <Circle cx="98" cy="48" r="18" fill={colors.white} stroke={colors.gray[400]} strokeWidth="1.5" />
      <Circle cx="98" cy="48" r="15" fill={colors.white} />
      {/* Clock marks */}
      <Rect x="97" y="35" width="2" height="4" rx="1" fill={colors.gray[400]} />
      <Rect x="97" y="57" width="2" height="4" rx="1" fill={colors.gray[400]} />
      <Rect x="84" y="47" width="4" height="2" rx="1" fill={colors.gray[400]} />
      <Rect x="108" y="47" width="4" height="2" rx="1" fill={colors.gray[400]} />
      {/* Clock hands */}
      <Path d="M98 48V39" stroke={colors.gray[600]} strokeWidth="2" strokeLinecap="round" />
      <Path d="M98 48L105 52" stroke={colors.gray[500]} strokeWidth="1.5" strokeLinecap="round" />
      <Circle cx="98" cy="48" r="2" fill={colors.gray[500]} />

      {/* Decorative dots */}
      <Circle cx="28" cy="56" r="2" fill={colors.gray[300]} opacity={0.5} />
      <Circle cx="116" cy="96" r="2.5" fill={colors.gray[300]} opacity={0.4} />
    </Svg>
  );
}
