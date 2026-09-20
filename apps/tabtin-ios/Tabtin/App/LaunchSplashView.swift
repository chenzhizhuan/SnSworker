import SwiftUI

/// 系统静态 LaunchScreen 后的原生接力层。
///
/// 视觉与已通过的移动端 HTML 样片保持同一时间轴，但不在冷启动关键路径创建 WebView，
/// 也不依赖网络资源。下层 RootView 会并行完成会话恢复与运行时初始化。
struct LaunchSplashView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.colorScheme) private var colorScheme
    let startedAt: Date

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 60.0, paused: reduceMotion)) { context in
            let elapsed = reduceMotion ? 2.5 : context.date.timeIntervalSince(startedAt)
            LaunchSplashFrame(elapsed: elapsed, isDark: colorScheme == .dark)
        }
        .ignoresSafeArea()
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("智算方舟正在准备你的工作现场")
        .accessibilityAddTraits(.updatesFrequently)
    }
}

private struct LaunchSplashFrame: View {
    let elapsed: TimeInterval
    let isDark: Bool

    private var ink: Color { isDark ? .white : Color(red: 32 / 255, green: 32 / 255, blue: 28 / 255) }
    private var paper: Color { isDark ? .black : .white }
    private var visualOpacity: Double { ramp(elapsed, from: 0, to: 0.28) * rampDown(elapsed, from: 3.74, to: 4.16) }
    private var ready: Bool { elapsed >= 2.86 }

    var body: some View {
        GeometryReader { proxy in
            let shortSide = min(proxy.size.width, proxy.size.height)
            let isPad = proxy.size.width >= 600
            let visualSize = isPad
                ? min(shortSide * (proxy.size.width > proxy.size.height ? 0.48 : 0.52), 500)
                : min(max(proxy.size.width * 0.74, 252), 332)
            let verticalOffset = isPad ? -proxy.size.height * 0.035 : -proxy.size.height * 0.025

            ZStack {
                paper

                VStack(spacing: isPad ? 40 : 32) {
                    LaunchSplashArtwork(
                        elapsed: elapsed,
                        ink: ink,
                        opacity: visualOpacity
                    )
                    .frame(width: visualSize, height: visualSize)

                    VStack(spacing: 12) {
                        Text("智算方舟")
                            .font(.system(size: isPad ? 28 : 24, weight: .heavy))
                            .tracking(-0.6)
                            .foregroundStyle(ink)

                        Text(ready ? "工作现场已就绪" : "正在准备你的工作现场")
                            .font(.system(size: isPad ? 16 : 14, weight: .medium))
                            .tracking(-0.3)
                            .foregroundStyle(ink.opacity(0.72))

                        HStack(spacing: 6) {
                            ForEach(0..<3, id: \.self) { index in
                                Circle()
                                    .fill(ink)
                                    .frame(width: 4, height: 4)
                                    .opacity(dotOpacity(index: index))
                            }
                        }
                    }
                    .opacity(ramp(elapsed, from: 0.62, to: 1.06) * rampDown(elapsed, from: 3.82, to: 4.14))
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .offset(y: verticalOffset)
            }
        }
    }

    private func dotOpacity(index: Int) -> Double {
        let local = (elapsed - 0.82 - Double(index) * 0.11).truncatingRemainder(dividingBy: 0.66)
        guard local >= 0 else { return 0.2 }
        let pulse = 1 - abs(local / 0.66 * 2 - 1)
        return 0.2 + pulse * 0.6
    }
}

private struct LaunchSplashArtwork: View {
    let elapsed: TimeInterval
    let ink: Color
    let opacity: Double

    var body: some View {
        Canvas { context, size in
            let center = CGPoint(x: size.width / 2, y: size.height / 2)
            let unit = size.width / 360

            strokeCircle(context: &context, center: center, radius: 154 * unit, color: ink.opacity(0.16), width: 1.5)
            strokeCircle(context: &context, center: center, radius: 119 * unit, color: ink, width: 3.2)
            strokeCircle(
                context: &context,
                center: center,
                radius: 84 * unit,
                color: ink.opacity(0.34),
                width: 1.5,
                dash: [5 * unit, 6 * unit]
            )

            let spinnerOpacity = ramp(elapsed, from: 1.76, to: 2.15) * rampDown(elapsed, from: 2.78, to: 3.6)
            if spinnerOpacity > 0 {
                let rotation = spinnerRotation(elapsed)
                var spinner = Path()
                spinner.addArc(
                    center: center,
                    radius: 154 * unit,
                    startAngle: .degrees(rotation - 90),
                    endAngle: .degrees(rotation),
                    clockwise: false
                )
                context.stroke(
                    spinner,
                    with: .color(ink.opacity(spinnerOpacity)),
                    style: StrokeStyle(lineWidth: 8 * unit, lineCap: .butt)
                )
            }

            drawArk(context: &context, center: center, unit: unit)
        }
        .opacity(opacity)
    }

    private func drawArk(context: inout GraphicsContext, center: CGPoint, unit: CGFloat) {
        let enter = ramp(elapsed, from: 0.26, to: 1.02)
        let scale = 0.78 + enter * 0.22
        let floatY = elapsed >= 1.34 && elapsed <= 2.32
            ? -4 * sin((elapsed - 1.34) / 0.98 * .pi) * unit
            : 0
        let markUnit = unit * scale
        let origin = CGPoint(
            x: center.x - 64 * markUnit,
            y: center.y - 52 * markUnit + floatY
        )
        let point: (CGFloat, CGFloat) -> CGPoint = { x, y in
            CGPoint(x: origin.x + x * markUnit, y: origin.y + y * markUnit)
        }

        let pixels: [(CGFloat, CGFloat)] = [(14, 45), (23, 33), (33, 48), (39, 19)]
        for (x, y) in pixels {
            let pixel = CGRect(
                x: origin.x + x * markUnit,
                y: origin.y + y * markUnit,
                width: 10 * markUnit,
                height: 10 * markUnit
            )
            context.fill(
                Path(roundedRect: pixel, cornerRadius: 2 * markUnit),
                with: .color(ink)
            )
        }

        var sail = Path()
        sail.move(to: point(48, 68))
        sail.addCurve(to: point(104, 8), control1: point(57, 42), control2: point(76, 21))
        sail.addLine(to: point(104, 59))
        sail.addCurve(to: point(48, 68), control1: point(82, 59), control2: point(64, 63))
        sail.closeSubpath()
        context.fill(sail, with: .color(ink))

        var upperWave = Path()
        upperWave.move(to: point(15, 70))
        upperWave.addCurve(to: point(72, 68), control1: point(37, 82), control2: point(55, 76))
        upperWave.addCurve(to: point(115, 68), control1: point(85, 62), control2: point(99, 62))
        upperWave.addLine(to: point(107, 83))
        upperWave.addCurve(to: point(62, 85), control1: point(91, 78), control2: point(77, 78))
        upperWave.addCurve(to: point(15, 70), control1: point(44, 93), control2: point(27, 88))
        upperWave.closeSubpath()
        context.fill(upperWave, with: .color(ink))

        var lowerWave = Path()
        lowerWave.move(to: point(51, 91))
        lowerWave.addCurve(to: point(108, 89), control1: point(68, 97), control2: point(82, 85))
        lowerWave.addCurve(to: point(51, 91), control1: point(89, 99), control2: point(69, 107))
        lowerWave.closeSubpath()
        context.fill(lowerWave, with: .color(ink))
    }

    private func strokeCircle(
        context: inout GraphicsContext,
        center: CGPoint,
        radius: CGFloat,
        color: Color,
        width: CGFloat,
        dash: [CGFloat] = []
    ) {
        let rect = CGRect(x: center.x - radius, y: center.y - radius, width: radius * 2, height: radius * 2)
        context.stroke(
            Path(ellipseIn: rect),
            with: .color(color),
            style: StrokeStyle(lineWidth: width, dash: dash)
        )
    }
}

private func ramp(_ value: TimeInterval, from start: TimeInterval, to end: TimeInterval) -> Double {
    guard end > start else { return value >= end ? 1 : 0 }
    return min(max((value - start) / (end - start), 0), 1)
}

private func rampDown(_ value: TimeInterval, from start: TimeInterval, to end: TimeInterval) -> Double {
    1 - ramp(value, from: start, to: end)
}

private func spinnerRotation(_ elapsed: TimeInterval) -> Double {
    if elapsed <= 2.78 {
        return 220 * easeInOutCubic(ramp(elapsed, from: 1.76, to: 2.78))
    }
    return 220 + 200 * easeOutQuart(ramp(elapsed, from: 2.78, to: 3.6))
}

private func easeInOutCubic(_ progress: Double) -> Double {
    progress < 0.5
        ? 4 * progress * progress * progress
        : 1 - pow(-2 * progress + 2, 3) / 2
}

private func easeOutQuart(_ progress: Double) -> Double {
    1 - pow(1 - progress, 4)
}
