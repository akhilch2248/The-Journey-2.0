//
//  AppStore.swift
//  The Journey
//
//  Session + data state for the whole app.
//

import Foundation
import SwiftUI

@MainActor
final class AppStore: ObservableObject {
    @Published var token: String?
    @Published var entries: [WeightEntry] = []   // ascending by date
    @Published var stats: WeightStats?
    @Published var goal: GoalProgress?
    @Published var isLoading = false
    @Published var errorMessage: String?

    @AppStorage("api_base") var apiBase: String = "http://127.0.0.1:8003"
    @AppStorage("unit") var unitRaw: String = WeightUnit.kg.rawValue

    var unit: WeightUnit {
        get { WeightUnit(rawValue: unitRaw) ?? .kg }
        set { unitRaw = newValue.rawValue }
    }

    var isSignedIn: Bool { token != nil }

    private var client: APIClient {
        APIClient(baseURL: URL(string: apiBase) ?? URL(string: "http://127.0.0.1:8003")!, token: token)
    }

    init() {
        token = Keychain.loadToken()
    }

    // MARK: Session

    func signIn(provider: String, devToken: String) async {
        errorMessage = nil
        do {
            let res = try await client.login(provider: provider, idToken: devToken)
            token = res.accessToken
            Keychain.saveToken(res.accessToken)
            await load()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func signOut() {
        token = nil
        Keychain.deleteToken()
        entries = []
        stats = nil
        goal = nil
    }

    // MARK: Data

    func load() async {
        guard isSignedIn else { return }
        isLoading = entries.isEmpty
        defer { isLoading = false }
        do {
            async let e = client.listWeights()
            async let s = client.stats()
            async let g = client.currentGoal()
            entries = try await e.sorted { $0.date < $1.date }
            stats = try await s
            goal = try await g
        } catch APIError.unauthorized {
            signOut()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func addEntry(date: Date, weight: Double, note: String) async -> Bool {
        await mutate {
            _ = try await self.client.createWeight(
                date: WeightEntry.dayFormatter.string(from: date),
                weightKg: self.unit.toKg(weight),
                note: note.isEmpty ? nil : note
            )
        }
    }

    func updateEntry(_ entry: WeightEntry, weight: Double, note: String) async -> Bool {
        await mutate {
            _ = try await self.client.updateWeight(
                id: entry.id,
                weightKg: self.unit.toKg(weight),
                note: note.isEmpty ? nil : note
            )
        }
    }

    func deleteEntry(_ entry: WeightEntry) async -> Bool {
        await mutate { try await self.client.deleteWeight(id: entry.id) }
    }

    func setGoal(targetWeight: Double, targetDate: Date?) async -> Bool {
        await mutate {
            _ = try await self.client.setGoal(
                targetWeightKg: self.unit.toKg(targetWeight),
                targetDate: targetDate.map { WeightEntry.dayFormatter.string(from: $0) }
            )
        }
    }

    /// Runs a mutation, refreshes on success, surfaces the error on failure.
    private func mutate(_ op: @escaping () async throws -> Void) async -> Bool {
        errorMessage = nil
        do {
            try await op()
            await load()
            return true
        } catch APIError.unauthorized {
            signOut()
            return false
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }
}

// MARK: - Units

enum WeightUnit: String, CaseIterable, Identifiable, Sendable {
    case kg, lb
    var id: String { rawValue }

    static let kgPerLb = 0.45359237

    func fromKg(_ kg: Double) -> Double { self == .kg ? kg : kg / Self.kgPerLb }
    func toKg(_ value: Double) -> Double { self == .kg ? value : value * Self.kgPerLb }

    /// "94.5 kg" in the display unit.
    func format(_ kg: Double?, signed: Bool = false, showUnit: Bool = true) -> String {
        guard let kg else { return "--" }
        let v = fromKg(kg)
        let prefix = signed && v > 0 ? "+" : ""
        let number = String(format: "%.1f", v)
        return showUnit ? "\(prefix)\(number) \(rawValue)" : "\(prefix)\(number)"
    }
}
