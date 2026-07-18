//
//  The_JourneyApp.swift
//  The Journey
//
//  Created by Akhil Chigurupaati on 2025-09-15.
//

import SwiftUI

@main
struct The_JourneyApp: App {
    @StateObject private var store = AppStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(store)
        }
    }
}
