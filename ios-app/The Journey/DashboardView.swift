//
//  DashboardView.swift
//  The Journey
//

import Charts
import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var store: AppStore
    @State private var showAdd = false
    @State private var showGoal = false
    @State private var editingEntry: WeightEntry?
    @State private var rangeDays: Int? = 30   // nil = all time

    var body: some View {
        NavigationStack {
            List {
                statsSection
                trendSection
                goalSection
                entriesSection
            }
            .navigationTitle("The Journey")
            .refreshable { await store.load() }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button { showAdd = true } label: {
                        Label("Log weight", systemImage: "plus")
                    }
                }
                ToolbarItem(placement: .secondaryAction) {
                    Picker("Unit", selection: store.$unitRaw) {
                        ForEach(WeightUnit.allCases) { u in
                            Text(u.rawValue).tag(u.rawValue)
                        }
                    }
                    .pickerStyle(.segmented)
                }
                ToolbarItem(placement: .secondaryAction) {
                    Button(role: .destructive) { store.signOut() } label: {
                        Label("Sign out", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }
            }
            .sheet(isPresented: $showAdd) { AddEntrySheet() }
            .sheet(isPresented: $showGoal) { GoalSheet() }
            .sheet(item: $editingEntry) { entry in EditEntrySheet(entry: entry) }
            .overlay {
                if store.isLoading { ProgressView() }
            }
            .task { await store.load() }
        }
    }

    // MARK: Stats

    private var statsSection: some View {
        Section {
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                statTile("Current", value: store.unit.format(store.stats?.latestWeightKg),
                         caption: store.stats?.latestDate.map { "as of \(prettyDay($0))" } ?? "")
                statTile("Since start", value: store.unit.format(store.stats?.totalChangeKg, signed: true),
                         caption: store.stats?.startWeightKg.map { "from \(store.unit.format($0))" } ?? "",
                         highlight: movingTowardGoal)
                statTile("7-day average", value: store.unit.format(store.stats?.movingAvg7dKg), caption: "")
                statTile("Pace", value: store.stats?.avgWeeklyChangeKg.map { "\(store.unit.format($0, signed: true))/wk" } ?? "--",
                         caption: "")
            }
            .listRowInsets(EdgeInsets())
            .listRowBackground(Color.clear)
        }
    }

    private var movingTowardGoal: Bool {
        guard let change = store.stats?.totalChangeKg, change != 0,
              let g = store.goal?.goal else { return false }
        let direction = g.targetWeightKg < g.startWeightKg ? -1.0 : 1.0
        return change * direction > 0
    }

    private func statTile(_ label: String, value: String, caption: String, highlight: Bool = false) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.caption).foregroundStyle(.secondary)
            Text(value)
                .font(.title3.weight(.semibold))
                .monospacedDigit()
                .contentTransition(.numericText())
            Text(caption)
                .font(.caption2)
                .foregroundStyle(highlight ? AnyShapeStyle(.green) : AnyShapeStyle(.tertiary))
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.background.secondary, in: RoundedRectangle(cornerRadius: 12))
    }

    // MARK: Trend

    private struct ChartPoint: Identifiable {
        let id: Int
        let day: Date
        let weight: Double   // display unit
        let avg: Double      // display unit
    }

    private var chartPoints: [ChartPoint] {
        let visible: [WeightEntry]
        if let rangeDays {
            let cutoff = Calendar.current.date(byAdding: .day, value: -rangeDays, to: .now) ?? .distantPast
            visible = store.entries.filter { $0.day >= cutoff }
        } else {
            visible = store.entries
        }
        return visible.map { entry in
            let end = entry.day
            let start = Calendar.current.date(byAdding: .day, value: -6, to: end) ?? end
            let window = visible.filter { $0.day >= start && $0.day <= end }
            let avg = window.reduce(0) { $0 + $1.weightKg } / Double(max(window.count, 1))
            return ChartPoint(
                id: entry.id,
                day: end,
                weight: store.unit.fromKg(entry.weightKg),
                avg: store.unit.fromKg(avg)
            )
        }
    }

    private var trendSection: some View {
        Section("Trend") {
            VStack(alignment: .leading, spacing: 12) {
                Picker("Range", selection: $rangeDays) {
                    Text("30D").tag(30 as Int?)
                    Text("90D").tag(90 as Int?)
                    Text("1Y").tag(365 as Int?)
                    Text("All").tag(nil as Int?)
                }
                .pickerStyle(.segmented)

                if chartPoints.count < 2 {
                    Text("Your trend line starts with two entries.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, minHeight: 120)
                } else {
                    trendChart
                }
            }
            .padding(.vertical, 4)
        }
    }

    private var trendChart: some View {
        let points = chartPoints
        let goalValue = store.goal.map { store.unit.fromKg($0.goal.targetWeightKg) }
        let weights = points.map(\.weight)
        let lo = min(weights.min() ?? 0, goalValue ?? .infinity)
        let hi = max(weights.max() ?? 1, goalValue ?? -.infinity)
        let padY = max((hi - lo) * 0.12, 0.5)

        return Chart {
            ForEach(points) { p in
                AreaMark(x: .value("Date", p.day), yStart: .value("Weight", lo - padY), yEnd: .value("Weight", p.weight))
                    .foregroundStyle(.linearGradient(
                        colors: [.green.opacity(0.14), .clear], startPoint: .top, endPoint: .bottom))
                LineMark(x: .value("Date", p.day), y: .value("Weight", p.weight))
                    .foregroundStyle(.green)
                    .lineStyle(StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
                LineMark(x: .value("Date", p.day), y: .value("Average", p.avg), series: .value("Series", "avg"))
                    .foregroundStyle(.secondary)
                    .lineStyle(StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
            }
            if let goalValue {
                RuleMark(y: .value("Goal", goalValue))
                    .foregroundStyle(.secondary)
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [5, 4]))
                    .annotation(position: .top, alignment: .trailing) {
                        Text("Goal \(String(format: "%.1f", goalValue)) \(store.unit.rawValue)")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }
            }
        }
        .chartYScale(domain: (lo - padY)...(hi + padY))
        .frame(height: 220)
    }

    // MARK: Goal

    private var goalSection: some View {
        Section {
            if let progress = store.goal {
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        goalNumber(store.unit.format(abs(progress.lostKg ?? 0)), caption: "done")
                        Spacer()
                        goalNumber(store.unit.format(abs(progress.remainingKg ?? 0)), caption: "to go")
                        Spacer()
                        goalNumber("\(Int((progress.percentComplete ?? 0).rounded()))%", caption: "complete")
                    }
                    ProgressView(value: min(max((progress.percentComplete ?? 0) / 100, 0), 1))
                        .tint(.green)
                    Text("\(store.unit.format(progress.goal.startWeightKg)) to \(store.unit.format(progress.goal.targetWeightKg))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 4)
            } else {
                Text("No goal yet. Set a target weight and watch the bar move.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        } header: {
            HStack {
                Text("Goal")
                Spacer()
                Button(store.goal == nil ? "Set goal" : "Change") { showGoal = true }
                    .font(.footnote)
                    .textCase(nil)
            }
        }
    }

    private func goalNumber(_ value: String, caption: String) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(value).font(.headline).monospacedDigit()
            Text(caption).font(.caption2).foregroundStyle(.secondary)
        }
    }

    // MARK: Entries

    private var entriesSection: some View {
        Section("Entries") {
            if store.entries.isEmpty && !store.isLoading {
                VStack(spacing: 6) {
                    Image(systemName: "square.and.pencil")
                        .font(.title2)
                        .foregroundStyle(.secondary)
                    Text("Nothing logged yet.").font(.subheadline.weight(.medium))
                    Text("Tap + to add today's weight.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
            }
            ForEach(store.entries.reversed()) { entry in
                entryRow(entry)
                    .swipeActions(edge: .trailing) {
                        Button(role: .destructive) {
                            Task { _ = await store.deleteEntry(entry) }
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                        Button {
                            editingEntry = entry
                        } label: {
                            Label("Edit", systemImage: "pencil")
                        }
                    }
            }
        }
    }

    private func entryRow(_ entry: WeightEntry) -> some View {
        HStack(spacing: 12) {
            Text(prettyDay(entry.date))
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .frame(width: 64, alignment: .leading)
            Text(store.unit.format(entry.weightKg))
                .font(.subheadline.weight(.semibold))
                .monospacedDigit()
            if let note = entry.note, !note.isEmpty {
                Text(note)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
        }
    }

    private func prettyDay(_ iso: String) -> String {
        guard let d = WeightEntry.dayFormatter.date(from: iso) else { return iso }
        return d.formatted(.dateTime.month(.abbreviated).day())
    }
}

// MARK: - Sheets

struct AddEntrySheet: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    @State private var weightText = ""
    @State private var date = Date()
    @State private var note = ""
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                TextField("Weight (\(store.unit.rawValue))", text: $weightText)
                    #if os(iOS)
                    .keyboardType(.decimalPad)
                    #endif
                DatePicker("Date", selection: $date, in: ...Date(), displayedComponents: .date)
                TextField("Note (optional)", text: $note)
                if let error {
                    Text(error).font(.footnote).foregroundStyle(.red)
                }
            }
            .navigationTitle("Log weight")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") { submit() }
                        .disabled(Double(weightText) == nil)
                }
            }
        }
        #if os(iOS)
        .presentationDetents([.medium])
        #endif
    }

    private func submit() {
        guard let weight = Double(weightText) else { return }
        Task {
            if await store.addEntry(date: date, weight: weight, note: note) {
                dismiss()
            } else {
                error = store.errorMessage
            }
        }
    }
}

struct EditEntrySheet: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    let entry: WeightEntry
    @State private var weightText = ""
    @State private var note = ""
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                TextField("Weight (\(store.unit.rawValue))", text: $weightText)
                    #if os(iOS)
                    .keyboardType(.decimalPad)
                    #endif
                TextField("Note (optional)", text: $note)
                if let error {
                    Text(error).font(.footnote).foregroundStyle(.red)
                }
            }
            .navigationTitle("Edit entry")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { submit() }
                        .disabled(Double(weightText) == nil)
                }
            }
            .onAppear {
                weightText = String(format: "%.1f", store.unit.fromKg(entry.weightKg))
                note = entry.note ?? ""
            }
        }
        #if os(iOS)
        .presentationDetents([.medium])
        #endif
    }

    private func submit() {
        guard let weight = Double(weightText) else { return }
        Task {
            if await store.updateEntry(entry, weight: weight, note: note) {
                dismiss()
            } else {
                error = store.errorMessage
            }
        }
    }
}

struct GoalSheet: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    @State private var weightText = ""
    @State private var hasDate = false
    @State private var date = Date()
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                TextField("Target weight (\(store.unit.rawValue))", text: $weightText)
                    #if os(iOS)
                    .keyboardType(.decimalPad)
                    #endif
                Toggle("Target date", isOn: $hasDate)
                if hasDate {
                    DatePicker("By", selection: $date, in: Date()..., displayedComponents: .date)
                }
                if let error {
                    Text(error).font(.footnote).foregroundStyle(.red)
                }
            }
            .navigationTitle("Set your goal")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { submit() }
                        .disabled(Double(weightText) == nil)
                }
            }
            .onAppear {
                if let g = store.goal?.goal {
                    weightText = String(format: "%.1f", store.unit.fromKg(g.targetWeightKg))
                    if let ds = g.targetDate, let d = WeightEntry.dayFormatter.date(from: ds) {
                        hasDate = true
                        date = d
                    }
                }
            }
        }
        #if os(iOS)
        .presentationDetents([.medium])
        #endif
    }

    private func submit() {
        guard let weight = Double(weightText) else { return }
        Task {
            if await store.setGoal(targetWeight: weight, targetDate: hasDate ? date : nil) {
                dismiss()
            } else {
                error = store.errorMessage
            }
        }
    }
}
