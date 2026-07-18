//
//  APIClient.swift
//  The Journey
//
//  Thin async URLSession wrapper around the backend API.
//

import Foundation

enum APIError: LocalizedError {
    case http(status: Int, detail: String)
    case network(underlying: Error)
    case unauthorized

    var errorDescription: String? {
        switch self {
        case .http(_, let detail): return detail
        case .network: return "Can't reach the server. Is the backend running?"
        case .unauthorized: return "Session expired. Sign in again."
        }
    }
}

struct APIClient: Sendable {
    var baseURL: URL
    var token: String?

    private struct APIDetail: Codable { let detail: String? }

    private func request(_ method: String, _ path: String, body: [String: Any?]? = nil) async throws -> Data {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            let clean = body.compactMapValues { $0 }
            req.httpBody = try JSONSerialization.data(withJSONObject: clean)
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: req)
        } catch {
            throw APIError.network(underlying: error)
        }

        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(status) else {
            if status == 401 { throw APIError.unauthorized }
            let detail = (try? JSONDecoder().decode(APIDetail.self, from: data))?.detail
            throw APIError.http(status: status, detail: detail ?? "Request failed (\(status))")
        }
        return data
    }

    private func get<T: Decodable>(_ path: String) async throws -> T {
        try JSONDecoder().decode(T.self, from: try await request("GET", path))
    }

    // MARK: Auth

    func login(provider: String, idToken: String) async throws -> TokenResponse {
        let data = try await request("POST", "auth/\(provider)", body: ["id_token": idToken])
        return try JSONDecoder().decode(TokenResponse.self, from: data)
    }

    func me() async throws -> UserProfile { try await get("auth/me") }

    // MARK: Weights

    func listWeights() async throws -> [WeightEntry] { try await get("weights?limit=1000") }

    func stats() async throws -> WeightStats { try await get("weights/stats") }

    func createWeight(date: String, weightKg: Double, note: String?) async throws -> WeightEntry {
        let data = try await request("POST", "weights", body: [
            "date": date, "weight_kg": weightKg, "note": note,
        ])
        return try JSONDecoder().decode(WeightEntry.self, from: data)
    }

    func updateWeight(id: Int, weightKg: Double?, note: String?) async throws -> WeightEntry {
        let data = try await request("PUT", "weights/\(id)", body: [
            "weight_kg": weightKg, "note": note,
        ])
        return try JSONDecoder().decode(WeightEntry.self, from: data)
    }

    func deleteWeight(id: Int) async throws {
        _ = try await request("DELETE", "weights/\(id)")
    }

    // MARK: Goals

    func currentGoal() async throws -> GoalProgress? {
        do {
            return try await get("goals/current") as GoalProgress
        } catch APIError.http(let status, _) where status == 404 {
            return nil
        }
    }

    func setGoal(targetWeightKg: Double, targetDate: String?) async throws -> Goal {
        let data = try await request("PUT", "goals", body: [
            "target_weight_kg": targetWeightKg, "target_date": targetDate,
        ])
        return try JSONDecoder().decode(Goal.self, from: data)
    }
}
