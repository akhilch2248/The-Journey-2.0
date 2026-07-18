//
//  ContentView.swift
//  The Journey
//

import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var store: AppStore

    var body: some View {
        if store.isSignedIn {
            DashboardView()
        } else {
            LoginView()
        }
    }
}

#Preview {
    ContentView().environmentObject(AppStore())
}
