package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class BankAccount_isOverdrawn_Test_Normal_8 {


    @Test
    public void testIsOverdrawnNormal() {
        BankAccount positiveBalanceAccount = new BankAccount("Alice", 100.0);
        BankAccount negativeBalanceAccount = new BankAccount("Bob", -50.0);

        Assertions.assertAll(
            () -> Assertions.assertFalse(positiveBalanceAccount.isOverdrawn(), "Account with positive balance should not be overdrawn"),
            () -> Assertions.assertTrue(negativeBalanceAccount.isOverdrawn(), "Account with negative balance should be overdrawn")
        );
    }

}
