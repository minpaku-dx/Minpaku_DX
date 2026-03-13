import Svg, { Path, Circle, Rect, G, Defs, LinearGradient, Stop } from 'react-native-svg';
import { colors } from '@/lib/theme';

type Props = { size?: number };

/**
 * Illustration: A building/house with a plus sign — no properties registered yet.
 */
export function NoPropertiesIllustration({ size = 140 }: Props) {
  return (
    <Svg width={size} height={size} viewBox="0 0 140 140" fill="none">
      <Defs>
        <LinearGradient id="pBgGrad" x1="70" y1="10" x2="70" y2="130" gradientUnits="userSpaceOnUse">
          <Stop offset="0" stopColor={colors.primary[100]} stopOpacity={0.4} />
          <Stop offset="1" stopColor={colors.primary[50]} stopOpacity={0.15} />
        </LinearGradient>
        <LinearGradient id="bldGrad" x1="70" y1="35" x2="70" y2="105" gradientUnits="userSpaceOnUse">
          <Stop offset="0" stopColor={colors.primary[100]} />
          <Stop offset="1" stopColor={colors.primary[200]} />
        </LinearGradient>
      </Defs>

      {/* Background circle */}
      <Circle cx="70" cy="70" r="58" fill="url(#pBgGrad)" />

      {/* Ground */}
      <Path
        d="M24 102C24 102 45 98 70 98C95 98 116 102 116 102"
        stroke={colors.primary[200]}
        strokeWidth="1.5"
        strokeLinecap="round"
      />

      {/* Building body */}
      <Rect x="44" y="42" width="40" height="56" rx="3" fill="url(#bldGrad)" stroke={colors.primary[400]} strokeWidth="1.5" />

      {/* Roof */}
      <Path
        d="M40 45L64 28L88 45"
        fill={colors.primary[50]}
        stroke={colors.primary[400]}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Windows row 1 */}
      <Rect x="52" y="50" width="9" height="9" rx="1.5" fill={colors.white} stroke={colors.primary[300]} strokeWidth="1" />
      <Rect x="67" y="50" width="9" height="9" rx="1.5" fill={colors.white} stroke={colors.primary[300]} strokeWidth="1" />

      {/* Windows row 2 */}
      <Rect x="52" y="65" width="9" height="9" rx="1.5" fill={colors.white} stroke={colors.primary[300]} strokeWidth="1" />
      <Rect x="67" y="65" width="9" height="9" rx="1.5" fill={colors.white} stroke={colors.primary[300]} strokeWidth="1" />

      {/* Door */}
      <Rect x="58" y="82" width="12" height="16" rx="2" fill={colors.primary[500]} opacity={0.3} stroke={colors.primary[400]} strokeWidth="1" />
      <Circle cx="67" cy="90" r="1.2" fill={colors.primary[500]} />

      {/* Plus circle */}
      <Circle cx="100" cy="44" r="16" fill={colors.primary[500]} />
      <Path
        d="M94 44H106M100 38V50"
        stroke={colors.white}
        strokeWidth="2.5"
        strokeLinecap="round"
      />

      {/* Small tree */}
      <Circle cx="102" cy="88" r="8" fill={colors.success[500]} opacity={0.25} />
      <Circle cx="102" cy="84" r="6" fill={colors.success[500]} opacity={0.3} />
      <Rect x="101" y="90" width="2" height="8" rx="1" fill={colors.gray[400]} opacity={0.4} />

      {/* Decorative dots */}
      <Circle cx="28" cy="50" r="2" fill={colors.primary[200]} opacity={0.5} />
      <Circle cx="118" cy="72" r="2.5" fill={colors.primary[200]} opacity={0.4} />
    </Svg>
  );
}
