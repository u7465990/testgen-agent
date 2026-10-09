package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertFalse;

public class BankAccount_isOverdrawn_Test_Path_9 {


    @Test
    public void testIsOverdrawnStatementCoverage() {
        // Path 1: balance < 0  -> returns true
        BankAccount overdrawnAccount = new BankAccount("Alice", -100.0);
        assertTrue(overdrawnAccount.isOverdrawn());

        // Path 2: balance >= 0 -> returns false
        BankAccount positiveAccount = new BankAccount("Bob", 100.0);
        assertFalse(positiveAccount.isOverdrawn());
    }

}
